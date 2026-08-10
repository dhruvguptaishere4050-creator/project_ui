import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.ai.analytics import (
    compute_at_risk_students,
    compute_class_analytics,
    compute_student_metrics,
)
from app.ai.insights import generate_insight
from app.database import get_db
from app.deps import assert_can_view_student, get_current_user, get_student_or_404, require_roles
from app.models import InsightReport, Parent, Role, SchoolClass, Student, Teacher, User, utcnow
from app.schemas import AtRiskStudent, ClassAnalytics, StudentInsight, StudentMetrics

router = APIRouter(prefix="/api/insights", tags=["insights"])

staff_only = require_roles(Role.admin, Role.teacher)


def _visible_students(db: Session, current_user: User) -> list[Student]:
    if current_user.role is Role.admin:
        return db.query(Student).all()
    if current_user.role is Role.teacher:
        teacher = db.query(Teacher).filter(Teacher.user_id == current_user.id).first()
        if teacher is None:
            return []
        class_ids = {subject.class_id for subject in teacher.subjects}
        return db.query(Student).filter(Student.class_id.in_(class_ids)).all() if class_ids else []
    if current_user.role is Role.parent:
        parent = db.query(Parent).filter(Parent.user_id == current_user.id).first()
        return list(parent.children) if parent else []
    student = db.query(Student).filter(Student.user_id == current_user.id).first()
    return [student] if student else []


@router.get("/students/{student_id}/metrics", response_model=StudentMetrics)
def student_metrics(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StudentMetrics:
    student = get_student_or_404(db, student_id)
    assert_can_view_student(db, current_user, student)
    return compute_student_metrics(db, student)


@router.post("/students/{student_id}", response_model=StudentInsight)
def student_insight(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StudentInsight:
    """Generate AI insights and recommendations for one student."""
    student = get_student_or_404(db, student_id)
    assert_can_view_student(db, current_user, student)

    metrics = compute_student_metrics(db, student)
    summary, recommendations, source = generate_insight(metrics)
    insight = StudentInsight(
        metrics=metrics,
        summary=summary,
        recommendations=recommendations,
        source=source,
        generated_at=utcnow(),
    )
    db.add(
        InsightReport(
            student_id=student.id,
            generated_by_id=current_user.id,
            source=source,
            payload=json.dumps(insight.model_dump(mode="json")),
        )
    )
    db.commit()
    return insight


@router.get("/students/{student_id}/history", response_model=list[StudentInsight])
def insight_history(
    student_id: int,
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[StudentInsight]:
    student = get_student_or_404(db, student_id)
    assert_can_view_student(db, current_user, student)
    reports = (
        db.query(InsightReport)
        .filter(InsightReport.student_id == student_id)
        .order_by(InsightReport.generated_at.desc())
        .limit(min(limit, 50))
        .all()
    )
    return [StudentInsight(**json.loads(report.payload)) for report in reports]


@router.get("/at-risk", response_model=list[AtRiskStudent])
def at_risk(
    min_risk_score: float = 25.0,
    class_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_only),
) -> list[AtRiskStudent]:
    students = _visible_students(db, current_user)
    if class_id is not None:
        students = [student for student in students if student.class_id == class_id]
    return compute_at_risk_students(db, students, min_risk_score)


@router.get("/classes/{class_id}", response_model=ClassAnalytics)
def class_analytics(
    class_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_only),
) -> ClassAnalytics:
    school_class = db.get(SchoolClass, class_id)
    if school_class is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Class not found")
    if current_user.role is Role.teacher:
        teacher = db.query(Teacher).filter(Teacher.user_id == current_user.id).first()
        teaches = teacher is not None and any(
            subject.class_id == class_id for subject in teacher.subjects
        )
        if not teaches:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="You do not teach this class"
            )
    return compute_class_analytics(db, school_class)
