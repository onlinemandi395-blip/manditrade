import GlassCard from "./GlassCard";

type ActionItem = {
  title: string;
  description: string;
  status: string;
  cta: string;
  amount: string;
};

type MyActionsPanelProps = {
  items: ActionItem[];
};

export default function MyActionsPanel({ items }: MyActionsPanelProps) {
  return (
    <section aria-labelledby="my-actions-title" className="stack">
      <div className="section-heading">
        <div>
          <p className="section-heading__eyebrow">Priority inbox</p>
          <h2 id="my-actions-title">My Actions</h2>
        </div>
        <button className="chip-button" type="button">
          Filter
        </button>
      </div>
      <div className="action-grid">
        {items.map((item) => (
          <GlassCard as="article" className="action-card" key={item.title}>
            <div className="action-card__meta">
              <span className={`badge badge--${item.status}`}>{item.status.replace("_", " ")}</span>
              <strong>{item.amount}</strong>
            </div>
            <h3>{item.title}</h3>
            <p>{item.description}</p>
            <button className="primary-button" type="button">
              {item.cta}
            </button>
          </GlassCard>
        ))}
      </div>
    </section>
  );
}
