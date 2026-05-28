import GlassCard from "./GlassCard";

type Product = {
  id: string;
  name: string;
  category: string;
  mandiPrice: string;
  mrp: string;
  stock: string;
  badge: string;
};

type ProductCardProps = {
  product: Product;
};

export default function ProductCard({ product }: ProductCardProps) {
  return (
    <GlassCard as="article" className="product-card">
      <div className="product-card__top">
        <span className={`badge badge--${product.badge}`}>{product.badge}</span>
        <span>{product.category}</span>
      </div>
      <h3>{product.name}</h3>
      <div className="product-card__prices">
        <strong>{product.mandiPrice}</strong>
        <span>{product.mrp}</span>
      </div>
      <p>{product.stock} in visible stock</p>
      <button className="primary-button" type="button">
        Open product
      </button>
    </GlassCard>
  );
}
