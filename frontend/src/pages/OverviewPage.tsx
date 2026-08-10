import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { apiFetch } from "../api/client";
import type { AtRiskStudent, ClassAnalytics, SchoolClass, Student } from "../api/types";
import { Card, ErrorMessage, Loading, RiskBadge, StatTile } from "../components/common";

export default function OverviewPage() {
  const [classes, setClasses] = useState<SchoolClass[]>([]);
  const [selectedClassId, setSelectedClassId] = useState<number | null>(null);
  const [analytics, setAnalytics] = useState<ClassAnalytics | null>(null);
  const [atRisk, setAtRisk] = useState<AtRiskStudent[]>([]);
  const [students, setStudents] = useState<Student[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [classList, risks, studentList] = await Promise.all([
        apiFetch<SchoolClass[]>("/api/classes"),
        apiFetch<AtRiskStudent[]>("/api/insights/at-risk"),
        apiFetch<Student[]>("/api/students"),
      ]);
      setClasses(classList);
      setAtRisk(risks);
      setStudents(studentList);
      const firstClass = classList[0]?.id ?? null;
      setSelectedClassId((current) => current ?? firstClass);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Failed to load overview");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (selectedClassId === null) return;
    apiFetch<ClassAnalytics>(`/api/insights/classes/${selectedClassId}`)
      .then(setAnalytics)
      .catch((caught: unknown) => {
        setAnalytics(null);
        setError(caught instanceof Error ? caught.message : "Failed to load class analytics");
      });
  }, [selectedClassId]);

  if (loading) return <Loading label="Loading dashboard..." />;

  return (
    <div className="stack">
      <ErrorMessage error={error} />

      <Card
        title="Class analytics"
        actions={
          <select
            value={selectedClassId ?? ""}
            onChange={(event) => setSelectedClassId(Number(event.target.value))}
          >
            {classes.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name} ({item.academic_year})
              </option>
            ))}
          </select>
        }
      >
        {analytics ? (
          <>
            <div className="stat-grid">
              <StatTile label="Students" value={String(analytics.students_count)} />
              <StatTile
                label="Average attendance"
                value={`${analytics.average_attendance.toFixed(1)}%`}
              />
              <StatTile label="Average score" value={`${analytics.average_score.toFixed(1)}%`} />
              <StatTile label="Needing support" value={String(analytics.at_risk_count)} />
            </div>
            <h3>Subject averages</h3>
            <table>
              <thead>
                <tr>
                  <th>Subject</th>
                  <th>Class average</th>
                  <th>Assessments</th>
                </tr>
              </thead>
              <tbody>
                {analytics.subject_averages.map((subject) => (
                  <tr key={subject.subject_id}>
                    <td>{subject.subject_name}</td>
                    <td>{subject.average_percentage.toFixed(1)}%</td>
                    <td>{subject.assessments_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </>
        ) : (
          <p className="muted">Select a class to view analytics.</p>
        )}
      </Card>

      <Card title="Students who may need additional support">
        {atRisk.length === 0 ? (
          <p className="muted">No students are currently flagged.</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Student</th>
                <th>Risk</th>
                <th>Attendance</th>
                <th>Average</th>
                <th>Why flagged</th>
              </tr>
            </thead>
            <tbody>
              {atRisk.map((item) => (
                <tr key={item.student_id}>
                  <td>
                    <Link to={`/students/${item.student_id}`}>{item.student_name}</Link>
                  </td>
                  <td>
                    <RiskBadge level={item.risk_level} /> {item.risk_score.toFixed(0)}
                  </td>
                  <td>{item.attendance_rate.toFixed(1)}%</td>
                  <td>{item.overall_average.toFixed(1)}%</td>
                  <td>
                    <ul className="reason-list">
                      {item.risk_reasons.map((reason) => (
                        <li key={reason}>{reason}</li>
                      ))}
                    </ul>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>

      <Card title="Students">
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>Roll number</th>
              <th>Email</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {students.map((student) => (
              <tr key={student.id}>
                <td>{student.user.full_name}</td>
                <td>{student.roll_number}</td>
                <td>{student.user.email}</td>
                <td>
                  <Link to={`/students/${student.id}`}>View record</Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  );
}
