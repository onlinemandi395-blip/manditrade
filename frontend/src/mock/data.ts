export const metrics = [
  { label: "Open RFQs", value: "18", status: "OPEN" },
  { label: "Ledger Exposure", value: "Rs 8.4L", status: "WARNING" },
  { label: "Low Stock Lines", value: "06", status: "HIGH_PRIORITY" },
  { label: "Workers Today", value: "24", status: "SUCCESS" },
];

export const actions = [
  {
    title: "Approve rice product request",
    description: "Two manufacturers proposed a new 25kg mandi rice pack.",
    status: "HIGH_PRIORITY",
    cta: "Review proposal",
    amount: "2 pending",
  },
  {
    title: "Confirm dispatch for client order",
    description: "Payment confirmed. Vehicle allocation is waiting.",
    status: "PENDING",
    cta: "Open dispatch",
    amount: "Rs 1.9L",
  },
  {
    title: "Review worker applications",
    description: "Packaging helper job has fresh local applications.",
    status: "OPEN",
    cta: "See workers",
    amount: "7 applicants",
  },
];

export const notifications = [
  {
    id: "n1",
    title: "RFQ Accepted",
    message: "A supplier accepted your rice RFQ for 200kg.",
    priority: "HIGH_PRIORITY",
    timestamp: "5 min ago",
    read: false,
  },
  {
    id: "n2",
    title: "Ledger Due Today",
    message: "Kumar Traders has Rs 60,000 due today.",
    priority: "OVERDUE",
    timestamp: "24 min ago",
    read: false,
  },
  {
    id: "n3",
    title: "Worker Shortlisted",
    message: "Ravi Kumar confirmed morning shift availability.",
    priority: "SUCCESS",
    timestamp: "1 hour ago",
    read: true,
  },
];

export const products = [
  {
    id: "p1",
    name: "Premium Rice",
    category: "Grain",
    mandiPrice: "Rs 42/kg",
    mrp: "Rs 51/kg",
    stock: "620 kg",
    badge: "ACTIVE",
  },
  {
    id: "p2",
    name: "Mustard Oil",
    category: "Oil",
    mandiPrice: "Rs 138/L",
    mrp: "Rs 152/L",
    stock: "240 L",
    badge: "OPEN",
  },
  {
    id: "p3",
    name: "Masoor Dal",
    category: "Pulse",
    mandiPrice: "Rs 86/kg",
    mrp: "Rs 96/kg",
    stock: "410 kg",
    badge: "PENDING",
  },
];

export const rfqs = [
  {
    id: "RFQ-2026-000041",
    title: "Need urgent rice stock",
    location: "Bhosari",
    qty: "200 kg",
    terms: "40% upfront, 15-day ledger",
    status: "OPEN",
  },
  {
    id: "RFQ-2026-000042",
    title: "Packaging helper replacement stock",
    location: "Manchar",
    qty: "90 kg",
    terms: "Cash on dispatch",
    status: "CONFIRMED",
  },
];

export const proposals = [
  {
    id: "ORD-2026-000018",
    client: "Kumar Traders",
    items: "Rice + Mustard Oil",
    value: "Rs 1.2L",
    status: "PENDING",
  },
  {
    id: "ORD-2026-000019",
    client: "Mahalaxmi Stores",
    items: "Dal + Oil",
    value: "Rs 86k",
    status: "DISPATCHED",
  },
];
