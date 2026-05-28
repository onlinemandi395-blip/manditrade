import { Link } from "react-router-dom";
import type { AppRoute } from "../app/routes";

type SidebarProps = {
  routes: AppRoute[];
  currentPath: string;
};

export default function Sidebar({ routes, currentPath }: SidebarProps) {
  const groupedRoutes = routes.reduce<Record<string, AppRoute[]>>((accumulator, route) => {
    accumulator[route.group] ??= [];
    accumulator[route.group].push(route);
    return accumulator;
  }, {});

  return (
    <nav className="sidebar glass-card" aria-label="Primary">
      <div className="sidebar__brand">
        <div className="sidebar__logo">DM</div>
        <div>
          <strong>Digital Manpur</strong>
          <p>Mandi operating shell</p>
        </div>
      </div>
      {Object.entries(groupedRoutes).map(([group, groupRoutes]) => (
        <div className="sidebar__group" key={group}>
          <span className="sidebar__group-label">{group}</span>
          {groupRoutes.map((route) => (
            <Link
              className={`sidebar__link ${currentPath === route.path ? "is-active" : ""}`}
              key={route.path}
              to={route.path}
            >
              {route.navLabel}
            </Link>
          ))}
        </div>
      ))}
    </nav>
  );
}
