import type { ReactNode } from "react";

export function Card({
  title,
  actions,
  children,
}: {
  title?: string;
  actions?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section className="card">
      {(title || actions) && (
        <header className="card-header">
          {title && <h2>{title}</h2>}
          {actions}
        </header>
      )}
      {children}
    </section>
  );
}

export function StatTile({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="stat-tile">
      <span className="stat-label">{label}</span>
      <span className="stat-value">{value}</span>
      {hint && <span className="stat-hint">{hint}</span>}
    </div>
  );
}

export function RiskBadge({ level }: { level: string }) {
  return <span className={`badge badge-${level}`}>{level} risk</span>;
}

export function TrendBadge({ trend }: { trend: string }) {
  return <span className={`badge badge-trend-${trend}`}>{trend}</span>;
}

export function Loading({ label = "Loading..." }: { label?: string }) {
  return <p className="muted">{label}</p>;
}

export function ErrorMessage({ error }: { error: string | null }) {
  if (!error) return null;
  return <p className="error" role="alert">{error}</p>;
}
