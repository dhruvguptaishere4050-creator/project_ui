from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import (
    assert_can_edit_student_records,
    assert_can_view_student,
    get_current_user,
    get_student_or_404,
    require_roles,
)
from app.models import (
    Assessment,
    Assignment,
    AssignmentSubmission,
    Attendance,
    Mark,
    Role,
    Subject,
    Teacher,
    User,
)
from app.schemas import (
    AssessmentCreate,
    AssessmentRead,
    AssignmentCreate,
    AssignmentRead,
    AttendanceBulkCreate,
    AttendanceRead,
    MarkCreate,
    MarkRead,
    SubmissionRead,
    SubmissionUpsert,
)

router = APIRouter(prefix="/api", tags=["academics"])

staff_only = require_roles(Role.admin, Role.teacher)


def get_subject_for_staff(db: Session, subject_id: int, current_user: User) -> Subject:
    subject = db.get(Subject, subject_id)
    if subject is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found")
    if current_user.role is Role.admin:
        return subject
    teacher = db.query(Teacher).filter(Teacher.user_id == current_user.id).first()
    if teacher is None or subject.teacher_id != teacher.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="You do not teach this subject"
        )
    return subject


# --- attendance -------------------------------------------------------------
@router.post("/attendance", response_model=list[AttendanceRead], status_code=201)
def record_attendance(
    payload: AttendanceBulkCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_only),
) -> list[Attendance]:
    records: list[Attendance] = []
    for entry in payload.entries:
        student = get_student_or_404(db, entry.student_id)
        assert_can_edit_student_records(db, current_user, student)
        if entry.subject_id is not None:
            get_subject_for_staff(db, entry.subject_id, current_user)
        existing = (
            db.query(Attendance)
            .filter(
                Attendance.student_id == entry.student_id,
                Attendance.subject_id == entry.subject_id,
                Attendance.session_date == entry.session_date,
            )
            .first()
        )
        if existing is not None:
            existing.status = entry.status
            existing.recorded_by_id = current_user.id
            records.append(existing)
            continue
        record = Attendance(**entry.model_dump(), recorded_by_id=current_user.id)
        db.add(record)
        records.append(record)
    db.commit()
    for record in records:
        db.refresh(record)
    return records


@router.get("/students/{student_id}/attendance", response_model=list[AttendanceRead])
def list_attendance(
    student_id: int,
    start_date: date | None = None,
    end_date: date | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Attendance]:
    student = get_student_or_404(db, student_id)
    assert_can_view_student(db, current_user, student)
    query = db.query(Attendance).filter(Attendance.student_id == student_id)
    if start_date is not None:
        query = query.filter(Attendance.session_date >= start_date)
    if end_date is not None:
        query = query.filter(Attendance.session_date <= end_date)
    return query.order_by(Attendance.session_date.desc()).all()


# --- assessments & marks ----------------------------------------------------
@router.post("/assessments", response_model=AssessmentRead, status_code=201)
def create_assessment(
    payload: AssessmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_only),
) -> Assessment:
    get_subject_for_staff(db, payload.subject_id, current_user)
    assessment = Assessment(**payload.model_dump())
    db.add(assessment)
    db.commit()
    db.refresh(assessment)
    return assessment


@router.get("/assessments", response_model=list[AssessmentRead])
def list_assessments(
    subject_id: int | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[Assessment]:
    query = db.query(Assessment)
    if subject_id is not None:
        query = query.filter(Assessment.subject_id == subject_id)
    return query.order_by(Assessment.held_on.desc()).all()


@router.post("/marks", response_model=MarkRead, status_code=201)
def upsert_mark(
    payload: MarkCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_only),
) -> Mark:
    assessment = db.get(Assessment, payload.assessment_id)
    if assessment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")
    get_subject_for_staff(db, assessment.subject_id, current_user)
    if payload.score > assessment.max_score:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Score cannot exceed the assessment maximum",
        )
    student = get_student_or_404(db, payload.student_id)
    assert_can_edit_student_records(db, current_user, student)

    mark = (
        db.query(Mark)
        .filter(Mark.assessment_id == payload.assessment_id, Mark.student_id == payload.student_id)
        .first()
    )
    if mark is None:
        mark = Mark(**payload.model_dump())
        db.add(mark)
    else:
        mark.score = payload.score
        mark.remarks = payload.remarks
    db.commit()
    db.refresh(mark)
    return mark


@router.get("/students/{student_id}/marks", response_model=list[MarkRead])
def list_marks(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Mark]:
    student = get_student_or_404(db, student_id)
    assert_can_view_student(db, current_user, student)
    return db.query(Mark).filter(Mark.student_id == student_id).all()


# --- assignments ------------------------------------------------------------
@router.post("/assignments", response_model=AssignmentRead, status_code=201)
def create_assignment(
    payload: AssignmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_only),
) -> Assignment:
    get_subject_for_staff(db, payload.subject_id, current_user)
    assignment = Assignment(**payload.model_dump())
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return assignment


@router.get("/assignments", response_model=list[AssignmentRead])
def list_assignments(
    subject_id: int | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[Assignment]:
    query = db.query(Assignment)
    if subject_id is not None:
        query = query.filter(Assignment.subject_id == subject_id)
    return query.order_by(Assignment.due_date.desc()).all()


@router.post("/submissions", response_model=SubmissionRead, status_code=201)
def upsert_submission(
    payload: SubmissionUpsert,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_only),
) -> AssignmentSubmission:
    assignment = db.get(Assignment, payload.assignment_id)
    if assignment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")
    get_subject_for_staff(db, assignment.subject_id, current_user)
    if payload.score is not None and payload.score > assignment.max_score:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Score cannot exceed the assignment maximum",
        )
    student = get_student_or_404(db, payload.student_id)
    assert_can_edit_student_records(db, current_user, student)

    submission = (
        db.query(AssignmentSubmission)
        .filter(
            AssignmentSubmission.assignment_id == payload.assignment_id,
            AssignmentSubmission.student_id == payload.student_id,
        )
        .first()
    )
    if submission is None:
        submission = AssignmentSubmission(**payload.model_dump())
        db.add(submission)
    else:
        submission.status = payload.status
        submission.submitted_on = payload.submitted_on
        submission.score = payload.score
        submission.feedback = payload.feedback
    db.commit()
    db.refresh(submission)
    return submission


@router.get("/students/{student_id}/submissions", response_model=list[SubmissionRead])
def list_submissions(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[AssignmentSubmission]:
    student = get_student_or_404(db, student_id)
    assert_can_view_student(db, current_user, student)
    return (
        db.query(AssignmentSubmission)
        .filter(AssignmentSubmission.student_id == student_id)
        .all()
    )
