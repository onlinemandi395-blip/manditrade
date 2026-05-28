export async function createMarketHero(
  canvas: HTMLCanvasElement,
  {
    reduceMotion = false,
    scene = "dashboard-hero",
  }: { reduceMotion?: boolean; scene?: "market-hero" | "dashboard-hero" | "login-hero" } = {},
) {
  const THREE = await import("three");

  const sceneGraph = new THREE.Scene();
  sceneGraph.fog = new THREE.Fog(0x13202b, 8, 28);

  const camera = new THREE.PerspectiveCamera(42, 1, 0.1, 100);
  camera.position.set(0, 4.5, 11);

  const renderer = new THREE.WebGLRenderer({
    canvas,
    antialias: true,
    alpha: true,
    powerPreference: "low-power",
  });

  const setSize = () => {
    const { clientWidth, clientHeight } = canvas;
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.5));
    renderer.setSize(clientWidth, clientHeight, false);
    camera.aspect = clientWidth / clientHeight;
    camera.updateProjectionMatrix();
  };
  setSize();

  const hemi = new THREE.HemisphereLight(0xf7ebdd, 0x13202b, 1.3);
  sceneGraph.add(hemi);

  const directional = new THREE.DirectionalLight(0xffffff, 1.05);
  directional.position.set(5, 8, 7);
  sceneGraph.add(directional);

  const root = new THREE.Group();
  sceneGraph.add(root);

  const road = new THREE.Mesh(
    new THREE.PlaneGeometry(18, 10, 20, 10),
    new THREE.MeshStandardMaterial({
      color: 0x20313d,
      roughness: 1,
      metalness: 0,
    }),
  );
  road.rotation.x = -Math.PI / 2.25;
  road.position.y = -1.8;
  root.add(road);

  const crateMaterial = new THREE.MeshStandardMaterial({
    color: 0xd8c7a1,
    roughness: 0.96,
    metalness: 0.03,
  });

  for (let index = 0; index < 18; index += 1) {
    const crate = new THREE.Mesh(
      new THREE.BoxGeometry(0.9, 0.9, 0.9),
      crateMaterial,
    );
    crate.position.set(
      -5 + (index % 6) * 1.6,
      -0.7 + Math.floor(index / 6) * 1.0,
      -2 - Math.floor(index / 6) * 0.4,
    );
    crate.rotation.y = ((index % 3) - 1) * 0.08;
    root.add(crate);
  }

  const truck = new THREE.Group();
  const truckBody = new THREE.Mesh(
    new THREE.BoxGeometry(2.2, 0.9, 1.1),
    new THREE.MeshStandardMaterial({ color: 0x2e6fb5, roughness: 0.85 }),
  );
  const truckCabin = new THREE.Mesh(
    new THREE.BoxGeometry(0.9, 0.75, 1.05),
    new THREE.MeshStandardMaterial({ color: 0xd9872c, roughness: 0.85 }),
  );
  truckCabin.position.set(1.25, 0.1, 0);
  truck.add(truckBody, truckCabin);
  truck.position.set(scene === "login-hero" ? 2.4 : 3.2, -0.6, 0.4);
  root.add(truck);

  let raf = 0;
  let active = true;

  const animate = (time: number) => {
    if (!active) {
      return;
    }

    if (!reduceMotion) {
      root.rotation.y = Math.sin(time * 0.00012) * (scene === "market-hero" ? 0.15 : 0.1);
      truck.position.x += Math.sin(time * 0.0004) * 0.0018;
      camera.position.y = 4.5 + Math.sin(time * 0.00018) * 0.12;
    }

    renderer.render(sceneGraph, camera);
    raf = requestAnimationFrame(animate);
  };

  const resizeObserver = new ResizeObserver(setSize);
  resizeObserver.observe(canvas);

  const visibilityHandler = () => {
    if (document.hidden) {
      active = false;
      cancelAnimationFrame(raf);
      return;
    }

    active = true;
    raf = requestAnimationFrame(animate);
  };

  document.addEventListener("visibilitychange", visibilityHandler);
  raf = requestAnimationFrame(animate);

  return () => {
    active = false;
    cancelAnimationFrame(raf);
    resizeObserver.disconnect();
    document.removeEventListener("visibilitychange", visibilityHandler);
    renderer.dispose();
  };
}
