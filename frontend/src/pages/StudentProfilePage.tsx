import { useCallback, useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { apiFetch } from "../api/client";
import type {
  AttendanceRecord,
  Student,
  StudentInsight,
  StudentMetrics,
  Submission,
} from "../api/types";
import { Card, ErrorMessage, Loading, RiskBadge, StatTile, TrendBadge } from "../components/common";

interface Props {
  studentId?: number;
}

export default function StudentProfilePage({ studentId: fixedId }: Props) {
  const params = useParams();
  const studentId = fixedId ?? Number(params.studentId);

  const [student, setStudent] = useState<Student | null>(null);
  const [metrics, setMetrics] = useState<StudentMetrics | null>(null);
  const [attendance, setAttendance] = useState<AttendanceRecord[]>([]);
  const [submissions, setSubmissions] = useState<Submission[]>([]);
  const [insight, setInsight] = useState<StudentInsight | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [studentData, metricsData, attendanceData, submissionData] = await Promise.all([
        apiFetch<Student>(`/api/students/${studentId}`),
        apiFetch<StudentMetrics>(`/api/insights/students/${studentId}/metrics`),
        apiFetch<AttendanceRecord[]>(`/api/students/${studentId}/attendance`),
        apiFetch<Submission[]>(`/api/students/${studentId}/submissions`),
      ]);
      setStudent(studentData);
      setMetrics(metricsData);
      setAttendance(attendanceData);
      setSubmissions(submissionData);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Failed to load student");
    } finally {
      setLoading(false);
    }
  }, [studentId]);

  useEffect(() => {
    void load();
  }, [load]);

  async function generateInsight() {
    setGenerating(true);
    setError(null);
    try {
      setInsight(await apiFetch<StudentInsight>(`/api/insights/students/${studentId}`, {
        method: "POST",
      }));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Failed to generate insight");
    } finally {
      setGenerating(false);
    }
  }

  if (loading) return <Loading label="Loading student record..." />;
  if (error && !metrics) return <ErrorMessage error={error} />;
  if (!student || !metrics) return null;

  const chartData = metrics.subject_performance.map((item) => ({
    name: item.subject_name,
    average: item.average_percentage,
  }));
  const recentAttendance = attendance.slice(0, 10);

  return (
    <div className="stack">
      <Card
        title={`${student.user.full_name} (${student.roll_number})`}
        actions={<RiskBadge level={metrics.risk_level} />}
      >
        <div className="stat-grid">
          <StatTile
            label="Attendance"
            value={`${metrics.attendance_rate.toFixed(1)}%`}
            hint={`${metrics.sessions_recorded} sessions recorded`}
          />
          <StatTile
            label="Overall average"
            value={`${metrics.overall_average.toFixed(1)}%`}
            hint={`Trend: ${metrics.marks_trend} (${metrics.trend_delta > 0 ? "+" : ""}${metrics.trend_delta.toFixed(1)} pts)`}
          />
          <StatTile
            label="Assignments completed"
            value={`${metrics.assignment_completion_rate.toFixed(0)}%`}
            hint={`${metrics.missing_assignments} missing`}
          />
          <StatTile label="Risk score" value={metrics.risk_score.toFixed(0)} hint="0 = no concern" />
        </div>
        <ul className="reason-list">
          {metrics.risk_reasons.map((reason) => (
            <li key={reason}>{reason}</li>
          ))}
        </ul>
      </Card>

      <Card title="Subject performance">
        {chartData.length === 0 ? (
          <p className="muted">No graded assessments yet.</p>
        ) : (
          <>
            <div style={{ width: "100%", height: 260 }}>
              <ResponsiveContainer>
                <BarChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" />
                  <YAxis domain={[0, 100]} />
                  <Tooltip />
                  <Legend />
                  <Bar dataKey="average" name="Average %" fill="#3b6fd4" />
                </BarChart>
              </ResponsiveContainer>
            </div>
            <table>
              <thead>
                <tr>
                  <th>Subject</th>
                  <th>Average</th>
                  <th>Assessments</th>
                  <th>Trend</th>
                </tr>
              </thead>
              <tbody>
                {metrics.subject_performance.map((item) => (
                  <tr key={item.subject_id}>
                    <td>{item.subject_name}</td>
                    <td>{item.average_percentage.toFixed(1)}%</td>
                    <td>{item.assessments_count}</td>
                    <td>
                      <TrendBadge trend={item.trend} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </>
        )}
      </Card>

      <Card
        title="AI academic insights"
        actions={
          <button type="button" onClick={generateInsight} disabled={generating}>
            {generating ? "Analysing..." : "Generate insights"}
          </button>
        }
      >
        <ErrorMessage error={error} />
        {insight ? (
          <>
            <p>{insight.summary}</p>
            <h3>Personalised recommendations</h3>
            <ol className="recommendations">
              {insight.recommendations.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ol>
            <p className="muted">
              Generated {new Date(insight.generated_at).toLocaleString()} via{" "}
              {insight.source === "llm" ? "language model" : "rule-based engine"}.
            </p>
          </>
        ) : (
          <p className="muted">
            Run the analysis to get a plain-language summary and study recommendations grounded in
            this student&apos;s attendance, marks and assignment data.
          </p>
        )}
      </Card>

      <div className="two-column">
        <Card title="Recent attendance">
          {recentAttendance.length === 0 ? (
            <p className="muted">No attendance recorded.</p>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {recentAttendance.map((record) => (
                  <tr key={record.id}>
                    <td>{record.session_date}</td>
                    <td>{record.status}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Card>

        <Card title="Assignments">
          {submissions.length === 0 ? (
            <p className="muted">No assignments recorded.</p>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Assignment</th>
                  <th>Status</th>
                  <th>Score</th>
                </tr>
              </thead>
              <tbody>
                {submissions.map((submission) => (
                  <tr key={submission.id}>
                    <td>#{submission.assignment_id}</td>
                    <td>{submission.status}</td>
                    <td>{submission.score ?? "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Card>
      </div>
    </div>
  );
}
