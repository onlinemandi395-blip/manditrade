import GlassCard from "./GlassCard";

type NotificationItem = {
  id: string;
  title: string;
  message: string;
  priority: string;
  timestamp: string;
  read: boolean;
};

type NotificationCenterProps = {
  open: boolean;
  items: NotificationItem[];
  onClose: () => void;
};

export default function NotificationCenter({
  open,
  items,
  onClose,
}: NotificationCenterProps) {
  return (
    <aside
      aria-hidden={!open}
      aria-label="Notifications"
      className={`notification-drawer ${open ? "is-open" : ""}`}
    >
      <GlassCard className="notification-drawer__panel">
        <div className="notification-drawer__header">
          <div>
            <p className="section-heading__eyebrow">Status feed</p>
            <h2>Notifications</h2>
          </div>
          <button className="icon-button" onClick={onClose} type="button">
            Close
          </button>
        </div>
        <div aria-live="polite" className="notification-list" role="log">
          {items.map((item) => (
            <article className="notification-card" key={item.id}>
              <div className="notification-card__row">
                <span className={`badge badge--${item.priority}`}>{item.priority}</span>
                <span>{item.timestamp}</span>
              </div>
              <h3>{item.title}</h3>
              <p>{item.message}</p>
              {!item.read ? <span className="notification-card__unread">Unread</span> : null}
            </article>
          ))}
        </div>
      </GlassCard>
    </aside>
  );
}
