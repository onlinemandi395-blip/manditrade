import GlassCard from "../components/GlassCard";
import type { PageProps } from "../app/routes";

export default function ProductPage({ products }: PageProps) {
  const product = products[0] as Record<string, string>;

  return (
    <div className="product-detail-layout">
      <GlassCard className="product-stage">
        <div className="product-stage__mock">
          <div className="product-stage__crate" />
          <div className="product-stage__shadow" />
        </div>
      </GlassCard>
      <GlassCard className="product-detail-card">
        <span className={`badge badge--${product.badge}`}>{product.badge}</span>
        <h2>{product.name}</h2>
        <p>
          Commodity-first detail layout for public marketplace pages. Keep this page flat enough
          for pricing clarity while preserving premium depth around the frame.
        </p>
        <div className="detail-list">
          <div>
            <span>Mandi price</span>
            <strong>{product.mandiPrice}</strong>
          </div>
          <div>
            <span>MRP</span>
            <strong>{product.mrp}</strong>
          </div>
          <div>
            <span>Visible stock</span>
            <strong>{product.stock}</strong>
          </div>
        </div>
        <button className="primary-button" type="button">
          Add to proposal
        </button>
      </GlassCard>
    </div>
  );
}
