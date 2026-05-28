type FilterBarProps = {
  filters: string[];
};

export default function FilterBar({ filters }: FilterBarProps) {
  return (
    <div className="filter-bar glass-card">
      <div className="filter-bar__search">
        <input aria-label="Filter products" placeholder="Search products, cities, categories" />
      </div>
      <div className="filter-bar__chips">
        {filters.map((filter) => (
          <button className="chip-button" key={filter} type="button">
            {filter}
          </button>
        ))}
      </div>
    </div>
  );
}
