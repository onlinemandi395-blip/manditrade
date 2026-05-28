import type { PropsWithChildren } from "react";

type GlassCardProps = PropsWithChildren<{
  className?: string;
  as?: "div" | "section" | "article";
}>;

export default function GlassCard({
  children,
  className = "",
  as = "div",
}: GlassCardProps) {
  const Component = as;

  return <Component className={`glass-card ${className}`.trim()}>{children}</Component>;
}
