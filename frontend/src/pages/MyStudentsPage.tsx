import { useEffect, useState } from "react";

import { apiFetch } from "../api/client";
import type { Student } from "../api/types";
import { ErrorMessage, Loading } from "../components/common";
import StudentProfilePage from "./StudentProfilePage";

/** Landing page for students and parents: shows their own (or their children's) records. */
export default function MyStudentsPage() {
  const [students, setStudents] = useState<Student[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiFetch<Student[]>("/api/students")
      .then((data) => {
        setStudents(data);
        setSelectedId(data[0]?.id ?? null);
      })
      .catch((caught: unknown) =>
        setError(caught instanceof Error ? caught.message : "Failed to load records"),
      )
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Loading />;
  if (error) return <ErrorMessage error={error} />;
  if (students.length === 0) return <p className="muted">No student records are linked to you.</p>;

  return (
    <div className="stack">
      {students.length > 1 && (
        <div className="tabs">
          {students.map((student) => (
            <button
              key={student.id}
              type="button"
              className={student.id === selectedId ? "tab tab-active" : "tab"}
              onClick={() => setSelectedId(student.id)}
            >
              {student.user.full_name}
            </button>
          ))}
        </div>
      )}
      {selectedId !== null && <StudentProfilePage key={selectedId} studentId={selectedId} />}
    </div>
  );
}
