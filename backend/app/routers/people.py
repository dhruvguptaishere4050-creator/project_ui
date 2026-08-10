from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import assert_can_view_student, get_current_user, get_student_or_404, require_roles
from app.models import Parent, Role, SchoolClass, Student, Subject, Teacher, User
from app.schemas import (
    ParentCreate,
    ParentRead,
    SchoolClassCreate,
    SchoolClassRead,
    StudentCreate,
    StudentRead,
    SubjectCreate,
    SubjectRead,
    TeacherCreate,
    TeacherRead,
    UserRead,
)
from app.security import hash_password

router = APIRouter(prefix="/api", tags=["people"])

admin_only = require_roles(Role.admin)
staff_only = require_roles(Role.admin, Role.teacher)


def _create_user(db: Session, payload, role: Role) -> User:
    email = payload.email.lower()
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="A user with this email already exists"
        )
    user = User(
        email=email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        role=role,
    )
    db.add(user)
    db.flush()
    return user


# --- classes ----------------------------------------------------------------
@router.post("/classes", response_model=SchoolClassRead, status_code=status.HTTP_201_CREATED)
def create_class(
    payload: SchoolClassCreate,
    db: Session = Depends(get_db),
    _: User = Depends(admin_only),
) -> SchoolClass:
    school_class = SchoolClass(**payload.model_dump())
    db.add(school_class)
    db.commit()
    db.refresh(school_class)
    return school_class


@router.get("/classes", response_model=list[SchoolClassRead])
def list_classes(
    db: Session = Depends(get_db), _: User = Depends(get_current_user)
) -> list[SchoolClass]:
    return db.query(SchoolClass).order_by(SchoolClass.name).all()


# --- subjects ---------------------------------------------------------------
@router.post("/subjects", response_model=SubjectRead, status_code=status.HTTP_201_CREATED)
def create_subject(
    payload: SubjectCreate, db: Session = Depends(get_db), _: User = Depends(admin_only)
) -> Subject:
    if db.get(SchoolClass, payload.class_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Class not found")
    if payload.teacher_id is not None and db.get(Teacher, payload.teacher_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Teacher not found")
    subject = Subject(**payload.model_dump())
    db.add(subject)
    db.commit()
    db.refresh(subject)
    return subject


@router.get("/subjects", response_model=list[SubjectRead])
def list_subjects(
    class_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Subject]:
    query = db.query(Subject)
    if class_id is not None:
        query = query.filter(Subject.class_id == class_id)
    if current_user.role is Role.teacher:
        teacher = db.query(Teacher).filter(Teacher.user_id == current_user.id).first()
        query = query.filter(Subject.teacher_id == (teacher.id if teacher else -1))
    elif current_user.role is Role.student:
        student = db.query(Student).filter(Student.user_id == current_user.id).first()
        query = query.filter(Subject.class_id == (student.class_id if student else -1))
    return query.order_by(Subject.name).all()


# --- teachers ---------------------------------------------------------------
@router.post("/teachers", response_model=TeacherRead, status_code=status.HTTP_201_CREATED)
def create_teacher(
    payload: TeacherCreate, db: Session = Depends(get_db), _: User = Depends(admin_only)
) -> Teacher:
    user = _create_user(db, payload.user, Role.teacher)
    teacher = Teacher(user_id=user.id, department=payload.department)
    db.add(teacher)
    db.commit()
    db.refresh(teacher)
    return teacher


@router.get("/teachers", response_model=list[TeacherRead])
def list_teachers(db: Session = Depends(get_db), _: User = Depends(admin_only)) -> list[Teacher]:
    return db.query(Teacher).all()


# --- students ---------------------------------------------------------------
@router.post("/students", response_model=StudentRead, status_code=status.HTTP_201_CREATED)
def create_student(
    payload: StudentCreate, db: Session = Depends(get_db), _: User = Depends(admin_only)
) -> Student:
    if db.query(Student).filter(Student.roll_number == payload.roll_number).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Roll number already in use"
        )
    if payload.class_id is not None and db.get(SchoolClass, payload.class_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Class not found")
    user = _create_user(db, payload.user, Role.student)
    student = Student(
        user_id=user.id,
        roll_number=payload.roll_number,
        class_id=payload.class_id,
        date_of_birth=payload.date_of_birth,
    )
    db.add(student)
    db.commit()
    db.refresh(student)
    return student


@router.get("/students", response_model=list[StudentRead])
def list_students(
    class_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Student]:
    """Returns only the students the caller is allowed to see."""
    query = db.query(Student)
    if class_id is not None:
        query = query.filter(Student.class_id == class_id)

    if current_user.role is Role.admin:
        return query.all()
    if current_user.role is Role.teacher:
        teacher = db.query(Teacher).filter(Teacher.user_id == current_user.id).first()
        class_ids = {subject.class_id for subject in teacher.subjects} if teacher else set()
        return [s for s in query.all() if s.class_id in class_ids]
    if current_user.role is Role.parent:
        parent = db.query(Parent).filter(Parent.user_id == current_user.id).first()
        child_ids = {child.id for child in parent.children} if parent else set()
        return [s for s in query.all() if s.id in child_ids]
    student = db.query(Student).filter(Student.user_id == current_user.id).first()
    return [student] if student else []


@router.get("/students/{student_id}", response_model=StudentRead)
def get_student(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Student:
    student = get_student_or_404(db, student_id)
    assert_can_view_student(db, current_user, student)
    return student


# --- parents ----------------------------------------------------------------
@router.post("/parents", response_model=ParentRead, status_code=status.HTTP_201_CREATED)
def create_parent(
    payload: ParentCreate, db: Session = Depends(get_db), _: User = Depends(admin_only)
) -> Parent:
    children = []
    for child_id in payload.child_ids:
        child = db.get(Student, child_id)
        if child is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Student {child_id} not found"
            )
        children.append(child)
    user = _create_user(db, payload.user, Role.parent)
    parent = Parent(user_id=user.id, phone=payload.phone, children=children)
    db.add(parent)
    db.commit()
    db.refresh(parent)
    return parent


@router.get("/parents", response_model=list[ParentRead])
def list_parents(db: Session = Depends(get_db), _: User = Depends(admin_only)) -> list[Parent]:
    return db.query(Parent).all()


@router.get("/users", response_model=list[UserRead])
def list_users(db: Session = Depends(get_db), _: User = Depends(admin_only)) -> list[User]:
    return db.query(User).order_by(User.id).all()


@router.patch("/users/{user_id}/status", response_model=UserRead)
def set_user_status(
    user_id: int,
    is_active: bool,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_only),
) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot disable your own account"
        )
    user.is_active = is_active
    db.commit()
    db.refresh(user)
    return user
