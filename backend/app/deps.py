from collections.abc import Callable, Iterable

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Parent, Role, Student, Teacher, User
from app.security import decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

CREDENTIALS_ERROR = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    payload = decode_token(token)
    if payload is None or not payload.get("sub"):
        raise CREDENTIALS_ERROR
    user = db.get(User, int(payload["sub"]))
    if user is None or not user.is_active:
        raise CREDENTIALS_ERROR
    return user


def require_roles(*roles: Role) -> Callable[[User], User]:
    allowed: Iterable[Role] = roles

    def dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions for this resource",
            )
        return current_user

    return dependency


def teacher_teaches_student(db: Session, teacher: Teacher, student: Student) -> bool:
    if student.class_id is None:
        return False
    return any(subject.class_id == student.class_id for subject in teacher.subjects)


def assert_can_view_student(db: Session, current_user: User, student: Student) -> None:
    """Central authorisation rule for every student-scoped read endpoint."""
    if current_user.role is Role.admin:
        return
    if current_user.role is Role.student:
        if student.user_id == current_user.id:
            return
    elif current_user.role is Role.parent:
        parent = db.query(Parent).filter(Parent.user_id == current_user.id).first()
        if parent and any(child.id == student.id for child in parent.children):
            return
    elif current_user.role is Role.teacher:
        teacher = db.query(Teacher).filter(Teacher.user_id == current_user.id).first()
        if teacher and teacher_teaches_student(db, teacher, student):
            return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to access this student"
    )


def assert_can_edit_student_records(db: Session, current_user: User, student: Student) -> None:
    if current_user.role is Role.admin:
        return
    if current_user.role is Role.teacher:
        teacher = db.query(Teacher).filter(Teacher.user_id == current_user.id).first()
        if teacher and teacher_teaches_student(db, teacher, student):
            return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to modify this student's records"
    )


def get_student_or_404(db: Session, student_id: int) -> Student:
    student = db.get(Student, student_id)
    if student is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")
    return student
