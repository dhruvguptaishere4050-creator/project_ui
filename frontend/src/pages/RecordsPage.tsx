import { useEffect, useState } from "react";
import type { FormEvent } from "react";

import { apiFetch } from "../api/client";
import type { Assessment, Student, Subject } from "../api/types";
import { Card, ErrorMessage } from "../components/common";

const TODAY = new Date().toISOString().slice(0, 10);

export default function RecordsPage() {
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [students, setStudents] = useState<Student[]>([]);
  const [assessments, setAssessments] = useState<Assessment[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const [subjectId, setSubjectId] = useState<number | null>(null);
  const [sessionDate, setSessionDate] = useState(TODAY);
  const [attendance, setAttendance] = useState<Record<number, string>>({});

  const [assessmentTitle, setAssessmentTitle] = useState("");
  const [assessmentType, setAssessmentType] = useState("quiz");
  const [maxScore, setMaxScore] = useState(100);

  const [markAssessmentId, setMarkAssessmentId] = useState<number | null>(null);
  const [scores, setScores] = useState<Record<number, string>>({});

  useEffect(() => {
    Promise.all([apiFetch<Subject[]>("/api/subjects"), apiFetch<Student[]>("/api/students")])
      .then(([subjectList, studentList]) => {
        setSubjects(subjectList);
        setStudents(studentList);
        setSubjectId(subjectList[0]?.id ?? null);
      })
      .catch((caught: unknown) =>
        setError(caught instanceof Error ? caught.message : "Failed to load data"),
      );
  }, []);

  useEffect(() => {
    if (subjectId === null) return;
    apiFetch<Assessment[]>(`/api/assessments?subject_id=${subjectId}`)
      .then((data) => {
        setAssessments(data);
        setMarkAssessmentId(data[0]?.id ?? null);
      })
      .catch(() => setAssessments([]));
  }, [subjectId]);

  const classStudents = students.filter((student) => {
    const subject = subjects.find((item) => item.id === subjectId);
    return subject ? student.class_id === subject.class_id : false;
  });

  async function submitAttendance(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setNotice(null);
    try {
      await apiFetch("/api/attendance", {
        method: "POST",
        body: JSON.stringify({
          entries: classStudents.map((student) => ({
            student_id: student.id,
            subject_id: subjectId,
            session_date: sessionDate,
            status: attendance[student.id] ?? "present",
          })),
        }),
      });
      setNotice(`Attendance saved for ${classStudents.length} student(s).`);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Failed to save attendance");
    }
  }

  async function createAssessment(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setNotice(null);
    try {
      const created = await apiFetch<Assessment>("/api/assessments", {
        method: "POST",
        body: JSON.stringify({
          subject_id: subjectId,
          title: assessmentTitle,
          assessment_type: assessmentType,
          max_score: maxScore,
          held_on: sessionDate,
        }),
      });
      setAssessments((current) => [created, ...current]);
      setMarkAssessmentId(created.id);
      setAssessmentTitle("");
      setNotice(`Assessment "${created.title}" created.`);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Failed to create assessment");
    }
  }

  async function submitMarks(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setNotice(null);
    if (markAssessmentId === null) return;
    try {
      for (const student of classStudents) {
        const raw = scores[student.id];
        if (raw === undefined || raw === "") continue;
        await apiFetch("/api/marks", {
          method: "POST",
          body: JSON.stringify({
            assessment_id: markAssessmentId,
            student_id: student.id,
            score: Number(raw),
          }),
        });
      }
      setNotice("Marks saved.");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Failed to save marks");
    }
  }

  return (
    <div className="stack">
      <ErrorMessage error={error} />
      {notice && <p className="notice">{notice}</p>}

      <Card title="Select subject">
        <div className="form-row">
          <label htmlFor="subject">Subject</label>
          <select
            id="subject"
            value={subjectId ?? ""}
            onChange={(event) => setSubjectId(Number(event.target.value))}
          >
            {subjects.map((subject) => (
              <option key={subject.id} value={subject.id}>
                {subject.name} ({subject.code})
              </option>
            ))}
          </select>
          <label htmlFor="date">Date</label>
          <input
            id="date"
            type="date"
            value={sessionDate}
            onChange={(event) => setSessionDate(event.target.value)}
          />
        </div>
      </Card>

      <Card title="Record attendance">
        <form onSubmit={submitAttendance}>
          <table>
            <thead>
              <tr>
                <th>Student</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {classStudents.map((student) => (
                <tr key={student.id}>
                  <td>{student.user.full_name}</td>
                  <td>
                    <select
                      value={attendance[student.id] ?? "present"}
                      onChange={(event) =>
                        setAttendance((current) => ({
                          ...current,
                          [student.id]: event.target.value,
                        }))
                      }
                    >
                      <option value="present">Present</option>
                      <option value="absent">Absent</option>
                      <option value="late">Late</option>
                      <option value="excused">Excused</option>
                    </select>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <button type="submit" disabled={classStudents.length === 0}>
            Save attendance
          </button>
        </form>
      </Card>

      <Card title="Create assessment">
        <form className="form-row" onSubmit={createAssessment}>
          <input
            placeholder="Title"
            value={assessmentTitle}
            onChange={(event) => setAssessmentTitle(event.target.value)}
            required
          />
          <select value={assessmentType} onChange={(event) => setAssessmentType(event.target.value)}>
            <option value="quiz">Quiz</option>
            <option value="midterm">Midterm</option>
            <option value="final">Final</option>
            <option value="project">Project</option>
            <option value="practical">Practical</option>
          </select>
          <input
            type="number"
            min={1}
            value={maxScore}
            onChange={(event) => setMaxScore(Number(event.target.value))}
          />
          <button type="submit">Create</button>
        </form>
      </Card>

      <Card title="Enter marks">
        <form onSubmit={submitMarks}>
          <div className="form-row">
            <label htmlFor="assessment">Assessment</label>
            <select
              id="assessment"
              value={markAssessmentId ?? ""}
              onChange={(event) => setMarkAssessmentId(Number(event.target.value))}
            >
              {assessments.map((assessment) => (
                <option key={assessment.id} value={assessment.id}>
                  {assessment.title} (max {assessment.max_score})
                </option>
              ))}
            </select>
          </div>
          <table>
            <thead>
              <tr>
                <th>Student</th>
                <th>Score</th>
              </tr>
            </thead>
            <tbody>
              {classStudents.map((student) => (
                <tr key={student.id}>
                  <td>{student.user.full_name}</td>
                  <td>
                    <input
                      type="number"
                      min={0}
                      value={scores[student.id] ?? ""}
                      onChange={(event) =>
                        setScores((current) => ({ ...current, [student.id]: event.target.value }))
                      }
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <button type="submit" disabled={markAssessmentId === null}>
            Save marks
          </button>
        </form>
      </Card>
    </div>
  );
}
