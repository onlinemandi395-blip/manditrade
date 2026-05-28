import type { ComponentType } from "react";
import DashboardPage from "../pages/DashboardPage";
import MarketplacePage from "../pages/MarketplacePage";
import ProductPage from "../pages/ProductPage";
import RFQPage from "../pages/RFQPage";
import ProposalPage from "../pages/ProposalPage";
import LedgerPage from "../pages/LedgerPage";
import NotificationsPage from "../pages/NotificationsPage";
import AdminConsolePage from "../pages/AdminConsolePage";
import LoginPage from "../pages/LoginPage";

export type PageProps = {
  actions: Array<Record<string, unknown>>;
  metrics: Array<Record<string, unknown>>;
  notifications: Array<Record<string, unknown>>;
  products: Array<Record<string, unknown>>;
  proposals: Array<Record<string, unknown>>;
  rfqs: Array<Record<string, unknown>>;
};

export type AppRoute = {
  path: string;
  label: string;
  navLabel: string;
  group: string;
  element: ComponentType<PageProps>;
};

export const appRoutes: AppRoute[] = [
  {
    path: "/dashboard",
    label: "Dashboard",
    navLabel: "Dashboard",
    group: "Workspace",
    element: DashboardPage,
  },
  {
    path: "/marketplace",
    label: "Marketplace",
    navLabel: "Marketplace",
    group: "Trade",
    element: MarketplacePage,
  },
  {
    path: "/product",
    label: "Product Detail",
    navLabel: "Product",
    group: "Trade",
    element: ProductPage,
  },
  {
    path: "/rfq",
    label: "RFQ Desk",
    navLabel: "RFQ",
    group: "Trade",
    element: RFQPage,
  },
  {
    path: "/proposal",
    label: "Proposal Orders",
    navLabel: "Proposals",
    group: "Trade",
    element: ProposalPage,
  },
  {
    path: "/ledger",
    label: "Ledger / Khata",
    navLabel: "Ledger",
    group: "Finance",
    element: LedgerPage,
  },
  {
    path: "/notifications",
    label: "Notifications",
    navLabel: "Notifications",
    group: "Workspace",
    element: NotificationsPage,
  },
  {
    path: "/admin",
    label: "Admin Console",
    navLabel: "Admin",
    group: "Governance",
    element: AdminConsolePage,
  },
  {
    path: "/login",
    label: "Login",
    navLabel: "Login",
    group: "Access",
    element: LoginPage,
  },
];
