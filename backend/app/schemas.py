from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models import AssessmentType, AttendanceStatus, Role, SubmissionStatus


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --- auth -------------------------------------------------------------------
class Token(BaseModel):
    """Short-lived access token; the refresh token travels in an HttpOnly cookie."""

    access_token: str
    token_type: str = "bearer"
    role: Role
    user_id: int
    full_name: str


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


# --- users ------------------------------------------------------------------
class UserBase(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=255)
    role: Role


class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)


class UserRead(ORMModel):
    id: int
    email: EmailStr
    full_name: str
    role: Role
    is_active: bool
    created_at: datetime


# --- classes & subjects -----------------------------------------------------
class SchoolClassCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    academic_year: str = Field(min_length=4, max_length=20)


class SchoolClassRead(ORMModel):
    id: int
    name: str
    academic_year: str


class SubjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    code: str = Field(min_length=1, max_length=40)
    class_id: int
    teacher_id: int | None = None


class SubjectRead(ORMModel):
    id: int
    name: str
    code: str
    class_id: int
    teacher_id: int | None


# --- people -----------------------------------------------------------------
class TeacherCreate(BaseModel):
    user: UserCreate
    department: str | None = None


class TeacherRead(ORMModel):
    id: int
    user: UserRead
    department: str | None


class StudentCreate(BaseModel):
    user: UserCreate
    roll_number: str = Field(min_length=1, max_length=40)
    class_id: int | None = None
    date_of_birth: date | None = None


class StudentRead(ORMModel):
    id: int
    roll_number: str
    class_id: int | None
    date_of_birth: date | None
    user: UserRead


class ParentCreate(BaseModel):
    user: UserCreate
    phone: str | None = None
    child_ids: list[int] = Field(default_factory=list)


class ParentRead(ORMModel):
    id: int
    user: UserRead
    phone: str | None
    children: list[StudentRead]


# --- attendance -------------------------------------------------------------
class AttendanceCreate(BaseModel):
    student_id: int
    subject_id: int | None = None
    session_date: date
    status: AttendanceStatus


class AttendanceBulkCreate(BaseModel):
    entries: list[AttendanceCreate] = Field(min_length=1)


class AttendanceRead(ORMModel):
    id: int
    student_id: int
    subject_id: int | None
    session_date: date
    status: AttendanceStatus


# --- assessments & marks ----------------------------------------------------
class AssessmentCreate(BaseModel):
    subject_id: int
    title: str = Field(min_length=1, max_length=200)
    assessment_type: AssessmentType
    max_score: float = Field(gt=0)
    held_on: date


class AssessmentRead(ORMModel):
    id: int
    subject_id: int
    title: str
    assessment_type: AssessmentType
    max_score: float
    held_on: date


class MarkCreate(BaseModel):
    assessment_id: int
    student_id: int
    score: float = Field(ge=0)
    remarks: str | None = None


class MarkRead(ORMModel):
    id: int
    assessment_id: int
    student_id: int
    score: float
    remarks: str | None


# --- assignments ------------------------------------------------------------
class AssignmentCreate(BaseModel):
    subject_id: int
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    max_score: float = Field(gt=0)
    due_date: date


class AssignmentRead(ORMModel):
    id: int
    subject_id: int
    title: str
    description: str | None
    max_score: float
    due_date: date


class SubmissionUpsert(BaseModel):
    assignment_id: int
    student_id: int
    status: SubmissionStatus
    submitted_on: date | None = None
    score: float | None = Field(default=None, ge=0)
    feedback: str | None = None


class SubmissionRead(ORMModel):
    id: int
    assignment_id: int
    student_id: int
    status: SubmissionStatus
    submitted_on: date | None
    score: float | None
    feedback: str | None


# --- analytics & insights ---------------------------------------------------
class SubjectPerformance(BaseModel):
    subject_id: int
    subject_name: str
    average_percentage: float
    assessments_count: int
    trend: str


class StudentMetrics(BaseModel):
    student_id: int
    student_name: str
    attendance_rate: float
    sessions_recorded: int
    overall_average: float
    marks_trend: str
    trend_delta: float
    assignment_completion_rate: float
    missing_assignments: int
    subject_performance: list[SubjectPerformance]
    weakest_subjects: list[str]
    strongest_subjects: list[str]
    risk_score: float
    risk_level: str
    risk_reasons: list[str]


class StudentInsight(BaseModel):
    metrics: StudentMetrics
    summary: str
    recommendations: list[str]
    source: str
    generated_at: datetime


class AtRiskStudent(BaseModel):
    student_id: int
    student_name: str
    class_id: int | None
    risk_score: float
    risk_level: str
    risk_reasons: list[str]
    attendance_rate: float
    overall_average: float


class ClassAnalytics(BaseModel):
    class_id: int
    class_name: str
    students_count: int
    average_attendance: float
    average_score: float
    at_risk_count: int
    subject_averages: list[SubjectPerformance]
    top_performers: list[AtRiskStudent]
    students_needing_support: list[AtRiskStudent]
