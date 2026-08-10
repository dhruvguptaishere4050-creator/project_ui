import { Link, Navigate, Route, Routes, useLocation } from "react-router-dom";
import type { ReactNode } from "react";

import { useAuth } from "./auth/AuthContext";
import { Loading } from "./components/common";
import type { Role } from "./api/types";
import AdminPeoplePage from "./pages/AdminPeoplePage";
import LoginPage from "./pages/LoginPage";
import MyStudentsPage from "./pages/MyStudentsPage";
import OverviewPage from "./pages/OverviewPage";
import RecordsPage from "./pages/RecordsPage";
import StudentProfilePage from "./pages/StudentProfilePage";

const STAFF: Role[] = ["admin", "teacher"];

function RequireAuth({ children, roles }: { children: ReactNode; roles?: Role[] }) {
  const { session, restoring } = useAuth();
  const location = useLocation();
  if (restoring) return <Loading label="Restoring your session..." />;
  if (!session) return <Navigate to="/login" state={{ from: location }} replace />;
  if (roles && !roles.includes(session.role)) return <Navigate to="/" replace />;
  return <>{children}</>;
}

function Shell({ children }: { children: ReactNode }) {
  const { session, signOut } = useAuth();
  if (!session) return <>{children}</>;
  const isStaff = STAFF.includes(session.role);
  return (
    <div className="app-shell">
      <header className="app-header">
        <div>
          <strong>Student Academic Management</strong>
          <nav>
            <Link to="/">{isStaff ? "Overview" : "My records"}</Link>
            {isStaff && <Link to="/records">Record data</Link>}
            {session.role === "admin" && <Link to="/people">People &amp; classes</Link>}
          </nav>
        </div>
        <div className="user-chip">
          <span>
            {session.full_name} · <em>{session.role}</em>
          </span>
          <button type="button" onClick={signOut}>
            Sign out
          </button>
        </div>
      </header>
      <main>{children}</main>
    </div>
  );
}

function Home() {
  const { session } = useAuth();
  if (!session) return null;
  return STAFF.includes(session.role) ? <OverviewPage /> : <MyStudentsPage />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/"
        element={
          <RequireAuth>
            <Shell>
              <Home />
            </Shell>
          </RequireAuth>
        }
      />
      <Route
        path="/students/:studentId"
        element={
          <RequireAuth>
            <Shell>
              <StudentProfilePage />
            </Shell>
          </RequireAuth>
        }
      />
      <Route
        path="/records"
        element={
          <RequireAuth roles={STAFF}>
            <Shell>
              <RecordsPage />
            </Shell>
          </RequireAuth>
        }
      />
      <Route
        path="/people"
        element={
          <RequireAuth roles={["admin"]}>
            <Shell>
              <AdminPeoplePage />
            </Shell>
          </RequireAuth>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
