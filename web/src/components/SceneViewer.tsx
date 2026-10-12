import { useEffect, useRef } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { bounds, deformedNodePositions, elementSegments, nodePositions } from "../cem/geometry";
import type { AnalysisResults, CemModel } from "../cem/types";

interface SceneViewerProps {
  model: CemModel;
  results: AnalysisResults | null;
  scale: number;
}

const UNDEFORMED_COLOR = 0x8a93a3;
const DEFORMED_COLOR = 0xd14b3a;
const NODE_COLOR = 0x4a5568;

/** Imperative Three.js scene, not @react-three/fiber -- deliberately
 * minimal (docs/MASTER_PLAN.md: "Web-first 3D viewer; not source of
 * truth"), so this stays a thin rendering layer over the pure geometry
 * helpers in cem/geometry.ts rather than its own framework. */
export function SceneViewer({ model, results, scale }: SceneViewerProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const sceneRef = useRef<THREE.Scene | null>(null);
  const groupRef = useRef<THREE.Group | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const controlsRef = useRef<OrbitControls | null>(null);

  // One-time scene/camera/renderer/controls setup.
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0xf6f3ec);
    sceneRef.current = scene;

    const camera = new THREE.PerspectiveCamera(
      50,
      container.clientWidth / container.clientHeight,
      0.01,
      1000,
    );
    cameraRef.current = camera;

    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setPixelRatio(window.devicePixelRatio);
    renderer.setSize(container.clientWidth, container.clientHeight);
    container.appendChild(renderer.domElement);

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controlsRef.current = controls;

    const group = new THREE.Group();
    scene.add(group);
    groupRef.current = group;

    const resize = () => {
      if (!container) return;
      camera.aspect = container.clientWidth / container.clientHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(container.clientWidth, container.clientHeight);
    };
    const resizeObserver = new ResizeObserver(resize);
    resizeObserver.observe(container);

    let frameId: number;
    const animate = () => {
      frameId = requestAnimationFrame(animate);
      controls.update();
      renderer.render(scene, camera);
    };
    animate();

    return () => {
      cancelAnimationFrame(frameId);
      resizeObserver.disconnect();
      controls.dispose();
      renderer.dispose();
      container.removeChild(renderer.domElement);
    };
  }, []);

  // Rebuild the drawn geometry whenever the model/results/scale change.
  useEffect(() => {
    const group = groupRef.current;
    const camera = cameraRef.current;
    const controls = controlsRef.current;
    if (!group || !camera || !controls) return;

    for (const child of [...group.children]) {
      group.remove(child);
      if (child instanceof THREE.Mesh || child instanceof THREE.Line) {
        child.geometry.dispose();
        if (Array.isArray(child.material)) {
          child.material.forEach((m) => m.dispose());
        } else {
          child.material.dispose();
        }
      }
    }

    const basePositions = nodePositions(model);
    const baseBounds = bounds(basePositions.values());
    const allPoints = [...basePositions.values()];

    addWireframe(group, elementSegments(model, basePositions), UNDEFORMED_COLOR, results !== null);
    addNodes(group, basePositions, NODE_COLOR, baseBounds.span);

    if (results) {
      const deformedPositions = deformedNodePositions(model, results, scale);
      addWireframe(group, elementSegments(model, deformedPositions), DEFORMED_COLOR, false);
      allPoints.push(...deformedPositions.values());
    }

    const b = bounds(allPoints);
    const distance = b.span * 1.8;
    camera.position.set(b.center.x + distance, b.center.y + distance * 0.7, b.center.z + distance);
    camera.near = Math.max(b.span / 1000, 1e-4);
    camera.far = distance * 100;
    camera.updateProjectionMatrix();
    controls.target.set(b.center.x, b.center.y, b.center.z);
    controls.update();
  }, [model, results, scale]);

  return <div ref={containerRef} style={{ width: "100%", height: "100%" }} />;
}

function addWireframe(
  group: THREE.Group,
  segments: ReturnType<typeof elementSegments>,
  color: number,
  dashed: boolean,
) {
  for (const seg of segments) {
    const geometry = new THREE.BufferGeometry().setFromPoints([
      new THREE.Vector3(seg.a.x, seg.a.y, seg.a.z),
      new THREE.Vector3(seg.b.x, seg.b.y, seg.b.z),
    ]);
    const material = dashed
      ? new THREE.LineDashedMaterial({ color, dashSize: 0.05, gapSize: 0.05 })
      : new THREE.LineBasicMaterial({ color, linewidth: 2 });
    const line = new THREE.Line(geometry, material);
    if (dashed) line.computeLineDistances();
    group.add(line);
  }
}

function addNodes(
  group: THREE.Group,
  positions: Map<string, { x: number; y: number; z: number }>,
  color: number,
  modelSpan: number,
) {
  const geometry = new THREE.SphereGeometry(1, 12, 12);
  const material = new THREE.MeshBasicMaterial({ color });
  const radius = modelSpan * 0.015;
  for (const pos of positions.values()) {
    const mesh = new THREE.Mesh(geometry, material);
    mesh.position.set(pos.x, pos.y, pos.z);
    mesh.scale.setScalar(radius);
    group.add(mesh);
  }
}
