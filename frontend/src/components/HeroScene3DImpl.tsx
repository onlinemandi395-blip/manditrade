import { useEffect, useRef, useState } from "react";
import { createMarketHero } from "../scenes/createMarketHero";
import { useSceneVisibility } from "../scenes/useSceneVisibility";
import HeroFallback from "./HeroFallback";

type HeroScene3DImplProps = {
  scene: "market-hero" | "dashboard-hero" | "login-hero";
  height: number;
};

export default function HeroScene3DImpl({ scene, height }: HeroScene3DImplProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const wrapperRef = useRef<HTMLDivElement | null>(null);
  const isVisible = useSceneVisibility(wrapperRef);
  const [webglFailed, setWebglFailed] = useState(false);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !isVisible) {
      return;
    }

    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    let cleanup: (() => void) | undefined;

    createMarketHero(canvas, { reduceMotion, scene })
      .then((dispose) => {
        cleanup = dispose;
      })
      .catch(() => {
        setWebglFailed(true);
      });

    return () => {
      cleanup?.();
    };
  }, [isVisible, scene]);

  if (webglFailed) {
    return <HeroFallback />;
  }

  return (
    <div className="hero-scene glass-card" ref={wrapperRef} style={{ minHeight: height }}>
      <canvas
        aria-hidden="true"
        className="hero-scene__canvas"
        ref={canvasRef}
        style={{ height }}
      />
      <div className="hero-scene__copy">
        <span className="badge badge--OPEN">{scene.replace("-", " ")}</span>
        <h2>Warm civic-industrial 3D surface for market-first trade workflows.</h2>
      </div>
    </div>
  );
}
