import GlassCard from "../components/GlassCard";
import type { PageProps } from "../app/routes";

export default function NotificationsPage({ notifications }: PageProps) {
  return (
    <div className="page-stack">
      <GlassCard className="page-hero">
        <p className="section-heading__eyebrow">Actionable feed</p>
        <h2>Notifications stay flat and readable, with blur limited to shell surfaces.</h2>
      </GlassCard>
      <section className="stack">
        {(notifications as Array<Record<string, string | boolean>>).map((item) => (
          <GlassCard as="article" className="notification-page-card" key={String(item.id)}>
            <div className="notification-card__row">
              <span className={`badge badge--${String(item.priority)}`}>{String(item.priority)}</span>
              <span>{String(item.timestamp)}</span>
            </div>
            <h3>{String(item.title)}</h3>
            <p>{String(item.message)}</p>
          </GlassCard>
        ))}
      </section>
    </div>
  );
}
