import GlassCard from "../components/GlassCard";
import type { PageProps } from "../app/routes";

export default function RFQPage({ rfqs }: PageProps) {
  return (
    <div className="page-stack">
      <GlassCard className="page-hero">
        <p className="section-heading__eyebrow">Negotiation desk</p>
        <h2>RFQ workflow stays data-dense and calm.</h2>
      </GlassCard>
      <div className="two-column-layout">
        <GlassCard as="section" className="stack">
          <h3>Request summary</h3>
          <p>Use this pane for the wizard, delivery location, and payment proposal summary.</p>
          <div className="timeline">
            <span className="badge badge--OPEN">OPEN</span>
            <span className="badge badge--PENDING">COUNTER</span>
            <span className="badge badge--CONFIRMED">CONFIRMED</span>
          </div>
        </GlassCard>
        <GlassCard as="section" className="stack">
          <h3>Live responses</h3>
          {(rfqs as Array<Record<string, string>>).map((rfq) => (
            <div className="inline-card" key={rfq.id}>
              <div>
                <strong>{rfq.title}</strong>
                <p>{rfq.terms}</p>
              </div>
              <span className={`badge badge--${rfq.status}`}>{rfq.status}</span>
            </div>
          ))}
        </GlassCard>
      </div>
    </div>
  );
}
