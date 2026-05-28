type TopBarProps = {
  title: string;
  unreadCount: number;
  onToggleNotifications: () => void;
};

export default function TopBar({ title, unreadCount, onToggleNotifications }: TopBarProps) {
  return (
    <header className="topbar glass-card">
      <div>
        <p className="topbar__eyebrow">Digital Bharat Mandi + Jobs Network</p>
        <h1>{title}</h1>
      </div>
      <div className="topbar__actions">
        <label className="topbar__search">
          <span className="sr-only">Search</span>
          <input aria-label="Search" placeholder="Search orders, RFQs, products" type="search" />
        </label>
        <button className="chip-button" type="button">
          Manufacturer
        </button>
        <button className="icon-button" onClick={onToggleNotifications} type="button">
          Bell
          <span className="icon-button__count">{unreadCount}</span>
        </button>
        <button className="chip-button" type="button">
          Brij Bihari
        </button>
      </div>
    </header>
  );
}
