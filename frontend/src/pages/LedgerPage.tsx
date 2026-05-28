import GlassCard from "../components/GlassCard";
import type { PageProps } from "../app/routes";

export default function LedgerPage(_: PageProps) {
  return (
    <div className="page-stack">
      <div className="ledger-strip">
        <GlassCard className="metric-card">
          <span className="badge badge--OVERDUE">OVERDUE</span>
          <strong>Rs 2.8L</strong>
          <p>Outstanding dues</p>
        </GlassCard>
        <GlassCard className="metric-card">
          <span className="badge badge--SUCCESS">COLLECTED</span>
          <strong>Rs 94k</strong>
          <p>Paid this week</p>
        </GlassCard>
        <GlassCard className="metric-card">
          <span className="badge badge--WARNING">UPCOMING</span>
          <strong>11</strong>
          <p>Due reminders queued</p>
        </GlassCard>
      </div>
      <GlassCard className="table-card">
        <h2>Ledger / Khata</h2>
        <div className="table-list">
          <div className="table-list__row table-list__row--head">
            <span>Party</span>
            <span>Due date</span>
            <span>Balance</span>
            <span>Status</span>
          </div>
          {[
            ["Kumar Traders", "05 Jun", "Rs 60,000", "PENDING"],
            ["Mahalaxmi Stores", "07 Jun", "Rs 18,500", "UPCOMING"],
            ["Ravi Labour Group", "Today", "Rs 6,400", "OVERDUE"],
          ].map((row) => (
            <div className="table-list__row" key={row.join("-")}>
              <span>{row[0]}</span>
              <span>{row[1]}</span>
              <strong>{row[2]}</strong>
              <span className={`badge badge--${row[3]}`}>{row[3]}</span>
            </div>
          ))}
        </div>
      </GlassCard>
    </div>
  );
}
