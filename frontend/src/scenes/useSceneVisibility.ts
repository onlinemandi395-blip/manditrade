import { useEffect, useState, type RefObject } from "react";

export function useSceneVisibility(ref: RefObject<Element>) {
  const [isVisible, setIsVisible] = useState(true);

  useEffect(() => {
    const node = ref.current;
    if (!node) {
      return;
    }

    const observer = new IntersectionObserver(
      ([entry]) => {
        setIsVisible(entry.isIntersecting);
      },
      { threshold: 0.15 },
    );

    observer.observe(node);
    return () => observer.disconnect();
  }, [ref]);

  return isVisible;
}
