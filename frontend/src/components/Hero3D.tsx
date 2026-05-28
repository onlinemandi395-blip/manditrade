import { lazy, Suspense } from "react";
import HeroFallback from "./HeroFallback";

const HeroScene3D = lazy(() => import("./HeroScene3DImpl"));

type Hero3DProps = {
  scene?: "market-hero" | "dashboard-hero" | "login-hero";
  height?: number;
};

export default function Hero3D({ scene = "dashboard-hero", height = 280 }: Hero3DProps) {
  return (
    <Suspense fallback={<HeroFallback />}>
      <HeroScene3D scene={scene} height={height} />
    </Suspense>
  );
}
