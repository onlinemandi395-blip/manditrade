import GlassCard from "./GlassCard";

type Metric = {
  label: string;
  value: string;
  status: string;
};

type KPIGridProps = {
  items: Metric[];
};

export default function KPIGrid({ items }: KPIGridProps) {
  return (
    <section aria-label="Key performance indicators" className="kpi-grid">
      {items.map((item) => (
        <GlassCard className="metric-card" key={item.label}>
          <span className={`badge badge--${item.status}`}>{item.status}</span>
          <strong>{item.value}</strong>
          <p>{item.label}</p>
        </GlassCard>
      ))}
    </section>
  );
}
