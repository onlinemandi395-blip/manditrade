import Hero3D from "../components/Hero3D";
import FilterBar from "../components/FilterBar";
import ProductCard from "../components/ProductCard";
import type { PageProps } from "../app/routes";

export default function MarketplacePage({ products }: PageProps) {
  return (
    <div className="page-stack">
      <Hero3D height={340} scene="market-hero" />
      <FilterBar filters={["Rice", "Oil", "Pulses", "Nearby", "Ready stock"]} />
      <section className="product-grid" aria-label="Marketplace products">
        {(products as never[]).map((product) => (
          <ProductCard key={(product as { id: string }).id} product={product} />
        ))}
      </section>
    </div>
  );
}
