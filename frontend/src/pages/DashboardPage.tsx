import Hero3D from "../components/Hero3D";
import KPIGrid from "../components/KPIGrid";
import MyActionsPanel from "../components/MyActionsPanel";
import GlassCard from "../components/GlassCard";
import type { PageProps } from "../app/routes";

export default function DashboardPage({ actions, metrics, rfqs }: PageProps) {
  return (
    <div className="page-stack">
      <Hero3D height={320} scene="dashboard-hero" />
      <KPIGrid items={metrics as never[]} />
      <div className="two-column-layout">
        <MyActionsPanel items={actions as never[]} />
        <GlassCard as="section" className="rail-card">
          <div className="section-heading">
            <div>
              <p className="section-heading__eyebrow">Live trade queue</p>
              <h2>RFQ Pulse</h2>
            </div>
          </div>
          <div className="stack">
            {(rfqs as Array<Record<string, string>>).map((rfq) => (
              <div className="inline-card" key={rfq.id}>
                <div>
                  <strong>{rfq.title}</strong>
                  <p>
                    {rfq.qty} · {rfq.location}
                  </p>
                </div>
                <span className={`badge badge--${rfq.status}`}>{rfq.status}</span>
              </div>
            ))}
          </div>
        </GlassCard>
      </div>
    </div>
  );
}
