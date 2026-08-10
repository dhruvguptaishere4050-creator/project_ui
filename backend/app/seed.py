"""Populate the database with a realistic demo dataset.

Run with: ``python -m app.seed``
"""

from __future__ import annotations

import random
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.database import Base, SessionLocal, engine
from app.models import (
    Assessment,
    AssessmentType,
    Assignment,
    AssignmentSubmission,
    Attendance,
    AttendanceStatus,
    Mark,
    Parent,
    Role,
    SchoolClass,
    Student,
    Subject,
    SubmissionStatus,
    Teacher,
    User,
)
from app.security import hash_password

DEMO_PASSWORD = "Password123!"

STUDENT_PROFILES = [
    ("Aarav Sharma", "S-101", 0.96, 0.86),
    ("Isha Patel", "S-102", 0.92, 0.78),
    ("Rohan Mehta", "S-103", 0.62, 0.38),
    ("Sara Khan", "S-104", 0.88, 0.71),
    ("Vikram Rao", "S-105", 0.70, 0.47),
    ("Neha Gupta", "S-106", 0.98, 0.91),
]

SUBJECTS = [("Mathematics", "MATH-10"), ("Physics", "PHY-10"), ("English", "ENG-10")]


def _user(db: Session, email: str, name: str, role: Role) -> User:
    user = User(
        email=email,
        full_name=name,
        hashed_password=hash_password(DEMO_PASSWORD),
        role=role,
    )
    db.add(user)
    db.flush()
    return user


def seed(db: Session) -> None:
    if db.query(User).count():
        print("Database already seeded; skipping.")
        return

    random.seed(7)
    _user(db, "admin@school.edu", "Priya Admin", Role.admin)

    school_class = SchoolClass(name="Grade 10-A", academic_year="2025-2026")
    db.add(school_class)
    db.flush()

    teacher_user = _user(db, "teacher@school.edu", "Anil Verma", Role.teacher)
    teacher = Teacher(user_id=teacher_user.id, department="Science & Mathematics")
    db.add(teacher)
    db.flush()

    subjects = []
    for name, code in SUBJECTS:
        subject = Subject(
            name=name, code=code, class_id=school_class.id, teacher_id=teacher.id
        )
        db.add(subject)
        subjects.append(subject)
    db.flush()

    students: list[Student] = []
    for index, (name, roll, attendance_rate, _ability) in enumerate(STUDENT_PROFILES):
        email = f"student{index + 1}@school.edu"
        user = _user(db, email, name, Role.student)
        student = Student(
            user_id=user.id,
            class_id=school_class.id,
            roll_number=roll,
            date_of_birth=date(2009, (index % 12) + 1, 15),
        )
        db.add(student)
        db.flush()
        students.append(student)

        # Attendance across the last 40 school days.
        for day_offset in range(40):
            session_date = date.today() - timedelta(days=day_offset + 1)
            if session_date.weekday() >= 5:
                continue
            present = random.random() < attendance_rate
            db.add(
                Attendance(
                    student_id=student.id,
                    subject_id=subjects[day_offset % len(subjects)].id,
                    session_date=session_date,
                    status=AttendanceStatus.present if present else AttendanceStatus.absent,
                    recorded_by_id=teacher_user.id,
                )
            )

    parent_user = _user(db, "parent@school.edu", "Meena Mehta", Role.parent)
    parent = Parent(user_id=parent_user.id, phone="+91-98765-43210", children=[students[2]])
    db.add(parent)

    # Assessments, marks, assignments and submissions.
    for subject in subjects:
        for week, assessment_type in enumerate(
            [AssessmentType.quiz, AssessmentType.quiz, AssessmentType.midterm], start=1
        ):
            assessment = Assessment(
                subject_id=subject.id,
                title=f"{subject.name} {assessment_type.value} {week}",
                assessment_type=assessment_type,
                max_score=100.0,
                held_on=date.today() - timedelta(days=40 - week * 10),
            )
            db.add(assessment)
            db.flush()
            for student, profile in zip(students, STUDENT_PROFILES, strict=True):
                ability = profile[3]
                # Rohan and Vikram drift downwards over the term.
                drift = -0.06 * week if ability < 0.5 else 0.02 * week
                score = max(0.0, min(100.0, (ability + drift) * 100 + random.uniform(-6, 6)))
                db.add(
                    Mark(
                        assessment_id=assessment.id,
                        student_id=student.id,
                        score=round(score, 1),
                    )
                )

        assignment = Assignment(
            subject_id=subject.id,
            title=f"{subject.name} weekly worksheet",
            description="Complete the practice worksheet and submit before the due date.",
            max_score=20.0,
            due_date=date.today() - timedelta(days=5),
        )
        db.add(assignment)
        db.flush()
        for student, profile in zip(students, STUDENT_PROFILES, strict=True):
            ability = profile[3]
            submitted = random.random() < (0.5 + ability / 2)
            db.add(
                AssignmentSubmission(
                    assignment_id=assignment.id,
                    student_id=student.id,
                    status=SubmissionStatus.graded if submitted else SubmissionStatus.missing,
                    submitted_on=assignment.due_date if submitted else None,
                    score=round(ability * 20, 1) if submitted else None,
                )
            )

    db.commit()
    print("Seeded demo data.")
    print(f"  admin@school.edu / {DEMO_PASSWORD}")
    print(f"  teacher@school.edu / {DEMO_PASSWORD}")
    print(f"  student1@school.edu / {DEMO_PASSWORD}")
    print(f"  parent@school.edu / {DEMO_PASSWORD}")


def main() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
