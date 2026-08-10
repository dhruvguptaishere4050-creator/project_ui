from __future__ import annotations

import enum
from datetime import date, datetime, timezone

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Role(str, enum.Enum):
    admin = "admin"
    teacher = "teacher"
    student = "student"
    parent = "parent"


class AttendanceStatus(str, enum.Enum):
    present = "present"
    absent = "absent"
    late = "late"
    excused = "excused"


class AssessmentType(str, enum.Enum):
    quiz = "quiz"
    midterm = "midterm"
    final = "final"
    project = "project"
    practical = "practical"


class SubmissionStatus(str, enum.Enum):
    pending = "pending"
    submitted = "submitted"
    late = "late"
    missing = "missing"
    graded = "graded"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[Role] = mapped_column(Enum(Role), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    # Bumped whenever credentials change; tokens carrying an older value are
    # rejected, so changing a password logs out every existing session.
    token_version: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    student: Mapped[Student | None] = relationship(back_populates="user", uselist=False)
    teacher: Mapped[Teacher | None] = relationship(back_populates="user", uselist=False)
    parent: Mapped[Parent | None] = relationship(back_populates="user", uselist=False)


class Teacher(Base):
    __tablename__ = "teachers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    department: Mapped[str | None] = mapped_column(String(120))

    user: Mapped[User] = relationship(back_populates="teacher")
    subjects: Mapped[list[Subject]] = relationship(back_populates="teacher")


class SchoolClass(Base):
    __tablename__ = "classes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    academic_year: Mapped[str] = mapped_column(String(20), nullable=False)

    __table_args__ = (UniqueConstraint("name", "academic_year", name="uq_class_name_year"),)

    students: Mapped[list[Student]] = relationship(back_populates="school_class")
    subjects: Mapped[list[Subject]] = relationship(back_populates="school_class")


class Student(Base):
    __tablename__ = "students"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    class_id: Mapped[int | None] = mapped_column(ForeignKey("classes.id", ondelete="SET NULL"))
    roll_number: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    date_of_birth: Mapped[date | None] = mapped_column(Date)

    user: Mapped[User] = relationship(back_populates="student")
    school_class: Mapped[SchoolClass | None] = relationship(back_populates="students")
    parents: Mapped[list[Parent]] = relationship(
        secondary="parent_student_links", back_populates="children"
    )
    attendance: Mapped[list[Attendance]] = relationship(
        back_populates="student", cascade="all, delete-orphan"
    )
    marks: Mapped[list[Mark]] = relationship(
        back_populates="student", cascade="all, delete-orphan"
    )
    submissions: Mapped[list[AssignmentSubmission]] = relationship(
        back_populates="student", cascade="all, delete-orphan"
    )


class Parent(Base):
    __tablename__ = "parents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    phone: Mapped[str | None] = mapped_column(String(40))

    user: Mapped[User] = relationship(back_populates="parent")
    children: Mapped[list[Student]] = relationship(
        secondary="parent_student_links", back_populates="parents"
    )


class ParentStudentLink(Base):
    __tablename__ = "parent_student_links"

    parent_id: Mapped[int] = mapped_column(
        ForeignKey("parents.id", ondelete="CASCADE"), primary_key=True
    )
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), primary_key=True
    )


class Subject(Base):
    __tablename__ = "subjects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    code: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id", ondelete="CASCADE"))
    teacher_id: Mapped[int | None] = mapped_column(ForeignKey("teachers.id", ondelete="SET NULL"))

    school_class: Mapped[SchoolClass] = relationship(back_populates="subjects")
    teacher: Mapped[Teacher | None] = relationship(back_populates="subjects")
    assignments: Mapped[list[Assignment]] = relationship(
        back_populates="subject", cascade="all, delete-orphan"
    )
    assessments: Mapped[list[Assessment]] = relationship(
        back_populates="subject", cascade="all, delete-orphan"
    )


class Attendance(Base):
    __tablename__ = "attendance"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"))
    subject_id: Mapped[int | None] = mapped_column(ForeignKey("subjects.id", ondelete="CASCADE"))
    session_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[AttendanceStatus] = mapped_column(Enum(AttendanceStatus), nullable=False)
    recorded_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))

    __table_args__ = (
        UniqueConstraint("student_id", "subject_id", "session_date", name="uq_attendance_entry"),
    )

    student: Mapped[Student] = relationship(back_populates="attendance")
    subject: Mapped[Subject | None] = relationship()


class Assessment(Base):
    __tablename__ = "assessments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    assessment_type: Mapped[AssessmentType] = mapped_column(Enum(AssessmentType), nullable=False)
    max_score: Mapped[float] = mapped_column(Float, nullable=False, default=100.0)
    held_on: Mapped[date] = mapped_column(Date, nullable=False)

    subject: Mapped[Subject] = relationship(back_populates="assessments")
    marks: Mapped[list[Mark]] = relationship(
        back_populates="assessment", cascade="all, delete-orphan"
    )


class Mark(Base):
    __tablename__ = "marks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    assessment_id: Mapped[int] = mapped_column(ForeignKey("assessments.id", ondelete="CASCADE"))
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"))
    score: Mapped[float] = mapped_column(Float, nullable=False)
    remarks: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (UniqueConstraint("assessment_id", "student_id", name="uq_mark_entry"),)

    assessment: Mapped[Assessment] = relationship(back_populates="marks")
    student: Mapped[Student] = relationship(back_populates="marks")


class Assignment(Base):
    __tablename__ = "assignments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    max_score: Mapped[float] = mapped_column(Float, nullable=False, default=100.0)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)

    subject: Mapped[Subject] = relationship(back_populates="assignments")
    submissions: Mapped[list[AssignmentSubmission]] = relationship(
        back_populates="assignment", cascade="all, delete-orphan"
    )


class AssignmentSubmission(Base):
    __tablename__ = "assignment_submissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    assignment_id: Mapped[int] = mapped_column(ForeignKey("assignments.id", ondelete="CASCADE"))
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"))
    status: Mapped[SubmissionStatus] = mapped_column(
        Enum(SubmissionStatus), default=SubmissionStatus.pending, nullable=False
    )
    submitted_on: Mapped[date | None] = mapped_column(Date)
    score: Mapped[float | None] = mapped_column(Float)
    feedback: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        UniqueConstraint("assignment_id", "student_id", name="uq_submission_entry"),
    )

    assignment: Mapped[Assignment] = relationship(back_populates="submissions")
    student: Mapped[Student] = relationship(back_populates="submissions")


class InsightReport(Base):
    """Cached AI-generated report for a student, kept for auditability."""

    __tablename__ = "insight_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"))
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    generated_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="rules")
    payload: Mapped[str] = mapped_column(Text, nullable=False)

    student: Mapped[Student] = relationship()


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    detail: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
