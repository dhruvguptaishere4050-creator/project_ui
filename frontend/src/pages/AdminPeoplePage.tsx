import { useEffect, useState } from "react";
import type { FormEvent } from "react";

import { apiFetch } from "../api/client";
import type { CurrentUser, SchoolClass, Student, Subject } from "../api/types";
import { Card, ErrorMessage } from "../components/common";

interface Teacher {
  id: number;
  user: CurrentUser;
  department: string | null;
}

export default function AdminPeoplePage() {
  const [classes, setClasses] = useState<SchoolClass[]>([]);
  const [teachers, setTeachers] = useState<Teacher[]>([]);
  const [students, setStudents] = useState<Student[]>([]);
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const [className, setClassName] = useState("");
  const [academicYear, setAcademicYear] = useState("2025-2026");

  const [teacherName, setTeacherName] = useState("");
  const [teacherEmail, setTeacherEmail] = useState("");
  const [teacherPassword, setTeacherPassword] = useState("");
  const [department, setDepartment] = useState("");

  const [subjectName, setSubjectName] = useState("");
  const [subjectCode, setSubjectCode] = useState("");
  const [subjectClassId, setSubjectClassId] = useState<number | null>(null);
  const [subjectTeacherId, setSubjectTeacherId] = useState<number | null>(null);

  const [studentName, setStudentName] = useState("");
  const [studentEmail, setStudentEmail] = useState("");
  const [studentPassword, setStudentPassword] = useState("");
  const [rollNumber, setRollNumber] = useState("");
  const [studentClassId, setStudentClassId] = useState<number | null>(null);

  const [parentName, setParentName] = useState("");
  const [parentEmail, setParentEmail] = useState("");
  const [parentPassword, setParentPassword] = useState("");
  const [childId, setChildId] = useState<number | null>(null);

  async function refresh() {
    try {
      const [classList, teacherList, studentList, subjectList] = await Promise.all([
        apiFetch<SchoolClass[]>("/api/classes"),
        apiFetch<Teacher[]>("/api/teachers"),
        apiFetch<Student[]>("/api/students"),
        apiFetch<Subject[]>("/api/subjects"),
      ]);
      setClasses(classList);
      setTeachers(teacherList);
      setStudents(studentList);
      setSubjects(subjectList);
      setSubjectClassId((current) => current ?? classList[0]?.id ?? null);
      setStudentClassId((current) => current ?? classList[0]?.id ?? null);
      setSubjectTeacherId((current) => current ?? teacherList[0]?.id ?? null);
      setChildId((current) => current ?? studentList[0]?.id ?? null);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Failed to load data");
    }
  }

  useEffect(() => {
    void refresh();
  }, []);

  async function submit(action: () => Promise<void>, successMessage: string) {
    setError(null);
    setNotice(null);
    try {
      await action();
      await refresh();
      setNotice(successMessage);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Request failed");
    }
  }

  function handleClass(event: FormEvent) {
    event.preventDefault();
    void submit(async () => {
      await apiFetch("/api/classes", {
        method: "POST",
        body: JSON.stringify({ name: className, academic_year: academicYear }),
      });
      setClassName("");
    }, "Class created.");
  }

  function handleTeacher(event: FormEvent) {
    event.preventDefault();
    void submit(async () => {
      await apiFetch("/api/teachers", {
        method: "POST",
        body: JSON.stringify({
          user: {
            email: teacherEmail,
            full_name: teacherName,
            role: "teacher",
            password: teacherPassword,
          },
          department,
        }),
      });
      setTeacherName("");
      setTeacherEmail("");
      setTeacherPassword("");
    }, "Teacher created.");
  }

  function handleSubject(event: FormEvent) {
    event.preventDefault();
    void submit(async () => {
      await apiFetch("/api/subjects", {
        method: "POST",
        body: JSON.stringify({
          name: subjectName,
          code: subjectCode,
          class_id: subjectClassId,
          teacher_id: subjectTeacherId,
        }),
      });
      setSubjectName("");
      setSubjectCode("");
    }, "Subject created.");
  }

  function handleStudent(event: FormEvent) {
    event.preventDefault();
    void submit(async () => {
      await apiFetch("/api/students", {
        method: "POST",
        body: JSON.stringify({
          user: {
            email: studentEmail,
            full_name: studentName,
            role: "student",
            password: studentPassword,
          },
          roll_number: rollNumber,
          class_id: studentClassId,
        }),
      });
      setStudentName("");
      setStudentEmail("");
      setStudentPassword("");
      setRollNumber("");
    }, "Student enrolled.");
  }

  function handleParent(event: FormEvent) {
    event.preventDefault();
    void submit(async () => {
      await apiFetch("/api/parents", {
        method: "POST",
        body: JSON.stringify({
          user: {
            email: parentEmail,
            full_name: parentName,
            role: "parent",
            password: parentPassword,
          },
          child_ids: childId === null ? [] : [childId],
        }),
      });
      setParentName("");
      setParentEmail("");
      setParentPassword("");
    }, "Parent linked.");
  }

  return (
    <div className="stack">
      <ErrorMessage error={error} />
      {notice && <p className="notice">{notice}</p>}

      <div className="two-column">
        <Card title="Create class">
          <form className="form-stack" onSubmit={handleClass}>
            <input
              placeholder="Class name"
              value={className}
              onChange={(event) => setClassName(event.target.value)}
              required
            />
            <input
              placeholder="Academic year"
              value={academicYear}
              onChange={(event) => setAcademicYear(event.target.value)}
              required
            />
            <button type="submit">Create class</button>
          </form>
        </Card>

        <Card title="Add teacher">
          <form className="form-stack" onSubmit={handleTeacher}>
            <input
              placeholder="Full name"
              value={teacherName}
              onChange={(event) => setTeacherName(event.target.value)}
              required
            />
            <input
              type="email"
              placeholder="Email"
              value={teacherEmail}
              onChange={(event) => setTeacherEmail(event.target.value)}
              required
            />
            <input
              type="password"
              placeholder="Temporary password (min 8 chars)"
              value={teacherPassword}
              onChange={(event) => setTeacherPassword(event.target.value)}
              minLength={8}
              required
            />
            <input
              placeholder="Department"
              value={department}
              onChange={(event) => setDepartment(event.target.value)}
            />
            <button type="submit">Add teacher</button>
          </form>
        </Card>

        <Card title="Add subject">
          <form className="form-stack" onSubmit={handleSubject}>
            <input
              placeholder="Subject name"
              value={subjectName}
              onChange={(event) => setSubjectName(event.target.value)}
              required
            />
            <input
              placeholder="Code"
              value={subjectCode}
              onChange={(event) => setSubjectCode(event.target.value)}
              required
            />
            <select
              value={subjectClassId ?? ""}
              onChange={(event) => setSubjectClassId(Number(event.target.value))}
            >
              {classes.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.name}
                </option>
              ))}
            </select>
            <select
              value={subjectTeacherId ?? ""}
              onChange={(event) => setSubjectTeacherId(Number(event.target.value))}
            >
              {teachers.map((teacher) => (
                <option key={teacher.id} value={teacher.id}>
                  {teacher.user.full_name}
                </option>
              ))}
            </select>
            <button type="submit">Add subject</button>
          </form>
        </Card>

        <Card title="Enrol student">
          <form className="form-stack" onSubmit={handleStudent}>
            <input
              placeholder="Full name"
              value={studentName}
              onChange={(event) => setStudentName(event.target.value)}
              required
            />
            <input
              type="email"
              placeholder="Email"
              value={studentEmail}
              onChange={(event) => setStudentEmail(event.target.value)}
              required
            />
            <input
              type="password"
              placeholder="Temporary password (min 8 chars)"
              value={studentPassword}
              onChange={(event) => setStudentPassword(event.target.value)}
              minLength={8}
              required
            />
            <input
              placeholder="Roll number"
              value={rollNumber}
              onChange={(event) => setRollNumber(event.target.value)}
              required
            />
            <select
              value={studentClassId ?? ""}
              onChange={(event) => setStudentClassId(Number(event.target.value))}
            >
              {classes.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.name}
                </option>
              ))}
            </select>
            <button type="submit">Enrol student</button>
          </form>
        </Card>

        <Card title="Link parent">
          <form className="form-stack" onSubmit={handleParent}>
            <input
              placeholder="Full name"
              value={parentName}
              onChange={(event) => setParentName(event.target.value)}
              required
            />
            <input
              type="email"
              placeholder="Email"
              value={parentEmail}
              onChange={(event) => setParentEmail(event.target.value)}
              required
            />
            <input
              type="password"
              placeholder="Temporary password (min 8 chars)"
              value={parentPassword}
              onChange={(event) => setParentPassword(event.target.value)}
              minLength={8}
              required
            />
            <select
              value={childId ?? ""}
              onChange={(event) => setChildId(Number(event.target.value))}
            >
              {students.map((student) => (
                <option key={student.id} value={student.id}>
                  {student.user.full_name}
                </option>
              ))}
            </select>
            <button type="submit">Link parent</button>
          </form>
        </Card>
      </div>

      <Card title="Subjects">
        <table>
          <thead>
            <tr>
              <th>Subject</th>
              <th>Code</th>
              <th>Class</th>
              <th>Teacher</th>
            </tr>
          </thead>
          <tbody>
            {subjects.map((subject) => (
              <tr key={subject.id}>
                <td>{subject.name}</td>
                <td>{subject.code}</td>
                <td>{classes.find((item) => item.id === subject.class_id)?.name ?? "-"}</td>
                <td>
                  {teachers.find((teacher) => teacher.id === subject.teacher_id)?.user.full_name ??
                    "Unassigned"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  );
}
