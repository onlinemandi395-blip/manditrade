import { useMemo, useState } from "react";
import { useLocation } from "react-router-dom";
import { appRoutes } from "./routes";
import Sidebar from "../components/Sidebar";
import TopBar from "../components/TopBar";
import NotificationCenter from "../components/NotificationCenter";
import {
  actions,
  metrics,
  notifications,
  products,
  proposals,
  rfqs,
} from "../mock/data";

const publicPaths = new Set(["/login", "/marketplace", "/product"]);

export default function AppShell() {
  const location = useLocation();
  const [notificationsOpen, setNotificationsOpen] = useState(false);

  const currentRoute = useMemo(
    () => appRoutes.find((route) => route.path === location.pathname) ?? appRoutes[0],
    [location.pathname],
  );

  const CurrentPage = currentRoute.element;
  const shellMode = publicPaths.has(location.pathname) ? "market" : "ops";

  return (
    <div className={`app-shell app-shell--${shellMode}`}>
      <div className="manpur-bg" aria-hidden="true">
        <div className="manpur-bg__orb manpur-bg__orb--left" />
        <div className="manpur-bg__orb manpur-bg__orb--right" />
        <div className="manpur-bg__lane" />
        <div className="manpur-bg__crate" />
        <div className="manpur-noise" />
      </div>
      <div className="app-shell__frame">
        <Sidebar routes={appRoutes} currentPath={location.pathname} />
        <div className="app-shell__main">
          <TopBar
            title={currentRoute.label}
            onToggleNotifications={() => setNotificationsOpen((value) => !value)}
            unreadCount={notifications.filter((item) => !item.read).length}
          />
          <main className="app-shell__content" role="main">
            <CurrentPage
              actions={actions}
              metrics={metrics}
              notifications={notifications}
              products={products}
              proposals={proposals}
              rfqs={rfqs}
            />
          </main>
        </div>
      </div>
      <NotificationCenter
        open={notificationsOpen}
        items={notifications}
        onClose={() => setNotificationsOpen(false)}
      />
    </div>
  );
}
