import GlassCard from "../components/GlassCard";
import type { PageProps } from "../app/routes";

export default function ProposalPage({ proposals }: PageProps) {
  return (
    <div className="page-stack">
      <GlassCard className="page-hero">
        <p className="section-heading__eyebrow">Proposal flow</p>
        <h2>Timeline-based order negotiation with room for terms, notes, and dispatch next steps.</h2>
      </GlassCard>
      <section className="stack">
        {(proposals as Array<Record<string, string>>).map((proposal) => (
          <GlassCard as="article" className="proposal-card" key={proposal.id}>
            <div className="proposal-card__head">
              <div>
                <strong>{proposal.client}</strong>
                <p>{proposal.items}</p>
              </div>
              <span className={`badge badge--${proposal.status}`}>{proposal.status}</span>
            </div>
            <div className="proposal-card__foot">
              <strong>{proposal.value}</strong>
              <button className="primary-button" type="button">
                Open proposal
              </button>
            </div>
          </GlassCard>
        ))}
      </section>
    </div>
  );
}
