import GlassCard from "../components/GlassCard";
import type { PageProps } from "../app/routes";

export default function AdminConsolePage({ actions }: PageProps) {
  return (
    <div className="page-stack">
      <GlassCard className="page-hero">
        <p className="section-heading__eyebrow">Governance console</p>
        <h2>Subtle civic grid, operational approvals, and runtime watch surfaces.</h2>
      </GlassCard>
      <div className="two-column-layout">
        <GlassCard as="section" className="stack">
          <h3>Approval queue</h3>
          {(actions as Array<Record<string, string>>).map((item) => (
            <div className="inline-card" key={item.title}>
              <div>
                <strong>{item.title}</strong>
                <p>{item.description}</p>
              </div>
              <button className="primary-button" type="button">
                {item.cta}
              </button>
            </div>
          ))}
        </GlassCard>
        <GlassCard as="section" className="stack">
          <h3>Runtime diagnostics</h3>
          <div className="inline-card">
            <strong>Drive runtime</strong>
            <span className="badge badge--SUCCESS">HEALTHY</span>
          </div>
          <div className="inline-card">
            <strong>Gmail queue</strong>
            <span className="badge badge--WARNING">2 retries</span>
          </div>
          <div className="inline-card">
            <strong>Onboarding secrets</strong>
            <span className="badge badge--OPEN">Vault-backed</span>
          </div>
        </GlassCard>
      </div>
    </div>
  );
}
