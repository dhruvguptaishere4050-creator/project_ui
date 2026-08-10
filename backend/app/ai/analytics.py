"""Deterministic analytics layer.

Everything the AI layer says about a student is grounded in the metrics computed
here, so insights stay explainable and reproducible.
"""

from __future__ import annotations

from statistics import fmean

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import (
    Assessment,
    Assignment,
    AssignmentSubmission,
    Attendance,
    AttendanceStatus,
    Mark,
    SchoolClass,
    Student,
    Subject,
    SubmissionStatus,
)
from app.schemas import AtRiskStudent, ClassAnalytics, StudentMetrics, SubjectPerformance

settings = get_settings()

PRESENT_STATUSES = {AttendanceStatus.present, AttendanceStatus.late, AttendanceStatus.excused}
COMPLETED_SUBMISSION_STATUSES = {
    SubmissionStatus.submitted,
    SubmissionStatus.late,
    SubmissionStatus.graded,
}


def _round(value: float, digits: int = 2) -> float:
    return round(float(value), digits)


def _trend_label(delta: float) -> str:
    if delta >= settings.marks_decline_threshold:
        return "improving"
    if delta <= -settings.marks_decline_threshold:
        return "declining"
    return "stable"


def _split_delta(percentages: list[float]) -> float:
    """Difference between the second-half and first-half averages."""
    if len(percentages) < 2:
        return 0.0
    midpoint = len(percentages) // 2
    first_half = percentages[:midpoint] or percentages[:1]
    second_half = percentages[midpoint:]
    return fmean(second_half) - fmean(first_half)


def compute_attendance(db: Session, student_id: int) -> tuple[float, int]:
    records = db.query(Attendance).filter(Attendance.student_id == student_id).all()
    if not records:
        return 0.0, 0
    present = sum(1 for record in records if record.status in PRESENT_STATUSES)
    return _round(present / len(records) * 100), len(records)


def _mark_rows(db: Session, student_id: int) -> list[tuple[Mark, Assessment, Subject]]:
    return (
        db.query(Mark, Assessment, Subject)
        .join(Assessment, Mark.assessment_id == Assessment.id)
        .join(Subject, Assessment.subject_id == Subject.id)
        .filter(Mark.student_id == student_id)
        .order_by(Assessment.held_on)
        .all()
    )


def compute_subject_performance(db: Session, student_id: int) -> list[SubjectPerformance]:
    rows = _mark_rows(db, student_id)
    by_subject: dict[int, dict[str, object]] = {}
    for mark, assessment, subject in rows:
        percentage = mark.score / assessment.max_score * 100 if assessment.max_score else 0.0
        bucket = by_subject.setdefault(subject.id, {"name": subject.name, "percentages": []})
        percentages: list[float] = bucket["percentages"]  # type: ignore[assignment]
        percentages.append(percentage)

    performance: list[SubjectPerformance] = []
    for subject_id, bucket in by_subject.items():
        percentages: list[float] = bucket["percentages"]  # type: ignore[assignment]
        performance.append(
            SubjectPerformance(
                subject_id=subject_id,
                subject_name=str(bucket["name"]),
                average_percentage=_round(fmean(percentages)),
                assessments_count=len(percentages),
                trend=_trend_label(_split_delta(percentages)),
            )
        )
    performance.sort(key=lambda item: item.average_percentage)
    return performance


def compute_assignment_stats(db: Session, student_id: int) -> tuple[float, int]:
    rows = (
        db.query(AssignmentSubmission)
        .join(Assignment, AssignmentSubmission.assignment_id == Assignment.id)
        .filter(AssignmentSubmission.student_id == student_id)
        .all()
    )
    if not rows:
        return 0.0, 0
    completed = sum(1 for row in rows if row.status in COMPLETED_SUBMISSION_STATUSES)
    missing = sum(
        1 for row in rows if row.status in {SubmissionStatus.missing, SubmissionStatus.pending}
    )
    return _round(completed / len(rows) * 100), missing


def _risk(
    attendance_rate: float,
    sessions_recorded: int,
    overall_average: float,
    trend_delta: float,
    completion_rate: float,
    missing_assignments: int,
    has_marks: bool,
) -> tuple[float, str, list[str]]:
    score = 0.0
    reasons: list[str] = []

    if sessions_recorded and attendance_rate < settings.attendance_risk_threshold:
        deficit = settings.attendance_risk_threshold - attendance_rate
        score += min(35.0, deficit)
        reasons.append(f"Attendance at {attendance_rate:.1f}% is below the expected 75%.")

    if has_marks and overall_average < settings.marks_risk_threshold:
        deficit = settings.marks_risk_threshold - overall_average
        score += min(35.0, deficit)
        reasons.append(f"Overall average of {overall_average:.1f}% is below the pass mark.")

    if has_marks and trend_delta <= -settings.marks_decline_threshold:
        score += min(20.0, abs(trend_delta))
        reasons.append(f"Scores declined by {abs(trend_delta):.1f} points across recent tests.")

    if missing_assignments:
        score += min(20.0, missing_assignments * 5)
        reasons.append(f"{missing_assignments} assignment(s) missing or unsubmitted.")

    if completion_rate and completion_rate < 60:
        score += 10.0
        reasons.append(f"Assignment completion rate is only {completion_rate:.1f}%.")

    score = _round(min(score, 100.0))
    if score >= 50:
        level = "high"
    elif score >= 25:
        level = "medium"
    else:
        level = "low"
    if not reasons:
        reasons.append("No academic risk indicators detected.")
    return score, level, reasons


def compute_student_metrics(db: Session, student: Student) -> StudentMetrics:
    attendance_rate, sessions_recorded = compute_attendance(db, student.id)
    subject_performance = compute_subject_performance(db, student.id)
    completion_rate, missing_assignments = compute_assignment_stats(db, student.id)

    rows = _mark_rows(db, student.id)
    percentages = [
        mark.score / assessment.max_score * 100
        for mark, assessment, _ in rows
        if assessment.max_score
    ]
    overall_average = _round(fmean(percentages)) if percentages else 0.0
    trend_delta = _round(_split_delta(percentages))

    risk_score, risk_level, risk_reasons = _risk(
        attendance_rate,
        sessions_recorded,
        overall_average,
        trend_delta,
        completion_rate,
        missing_assignments,
        bool(percentages),
    )

    return StudentMetrics(
        student_id=student.id,
        student_name=student.user.full_name,
        attendance_rate=attendance_rate,
        sessions_recorded=sessions_recorded,
        overall_average=overall_average,
        marks_trend=_trend_label(trend_delta),
        trend_delta=trend_delta,
        assignment_completion_rate=completion_rate,
        missing_assignments=missing_assignments,
        subject_performance=subject_performance,
        weakest_subjects=[item.subject_name for item in subject_performance[:2]],
        strongest_subjects=[item.subject_name for item in reversed(subject_performance[-2:])],
        risk_score=risk_score,
        risk_level=risk_level,
        risk_reasons=risk_reasons,
    )


def _as_at_risk(metrics: StudentMetrics, class_id: int | None) -> AtRiskStudent:
    return AtRiskStudent(
        student_id=metrics.student_id,
        student_name=metrics.student_name,
        class_id=class_id,
        risk_score=metrics.risk_score,
        risk_level=metrics.risk_level,
        risk_reasons=metrics.risk_reasons,
        attendance_rate=metrics.attendance_rate,
        overall_average=metrics.overall_average,
    )


def compute_at_risk_students(
    db: Session, students: list[Student], min_risk_score: float = 25.0
) -> list[AtRiskStudent]:
    flagged = [
        _as_at_risk(metrics, student.class_id)
        for student in students
        if (metrics := compute_student_metrics(db, student)).risk_score >= min_risk_score
    ]
    flagged.sort(key=lambda item: item.risk_score, reverse=True)
    return flagged


def compute_class_analytics(db: Session, school_class: SchoolClass) -> ClassAnalytics:
    students = school_class.students
    all_metrics = [compute_student_metrics(db, student) for student in students]

    attendance_values = [m.attendance_rate for m in all_metrics if m.sessions_recorded]
    score_values = [m.overall_average for m in all_metrics if m.overall_average]

    subject_totals: dict[int, dict[str, object]] = {}
    for metrics in all_metrics:
        for subject in metrics.subject_performance:
            bucket = subject_totals.setdefault(
                subject.subject_id, {"name": subject.subject_name, "values": [], "count": 0}
            )
            bucket["values"].append(subject.average_percentage)  # type: ignore[union-attr]
            bucket["count"] = int(bucket["count"]) + subject.assessments_count

    subject_averages = [
        SubjectPerformance(
            subject_id=subject_id,
            subject_name=str(bucket["name"]),
            average_percentage=_round(fmean(bucket["values"])),  # type: ignore[arg-type]
            assessments_count=int(bucket["count"]),
            trend="stable",
        )
        for subject_id, bucket in subject_totals.items()
    ]
    subject_averages.sort(key=lambda item: item.average_percentage)

    ranked = sorted(all_metrics, key=lambda m: m.overall_average, reverse=True)
    students_by_id = {student.id: student for student in students}
    needing_support = sorted(
        (m for m in all_metrics if m.risk_score >= 25.0),
        key=lambda m: m.risk_score,
        reverse=True,
    )

    return ClassAnalytics(
        class_id=school_class.id,
        class_name=school_class.name,
        students_count=len(students),
        average_attendance=_round(fmean(attendance_values)) if attendance_values else 0.0,
        average_score=_round(fmean(score_values)) if score_values else 0.0,
        at_risk_count=len(needing_support),
        subject_averages=subject_averages,
        top_performers=[
            _as_at_risk(m, students_by_id[m.student_id].class_id) for m in ranked[:3]
        ],
        students_needing_support=[
            _as_at_risk(m, students_by_id[m.student_id].class_id) for m in needing_support
        ],
    )
