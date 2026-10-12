import { forwardRef, useEffect, useImperativeHandle, useRef } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { bounds, deformedNodePositions, elementSegments, nodePositions } from "../cem/geometry";
import type { AnalysisResults, CemModel } from "../cem/types";

interface SceneViewerProps {
  model: CemModel;
  results: AnalysisResults | null;
  scale: number;
}

export interface SceneViewerHandle {
  /** A PNG data URL of the current frame, or null if not yet rendered.
   * Used by the print report to embed a static snapshot instead of a
   * live (non-printable) WebGL canvas. */
  capture: () => string | null;
  /** True once the canvas has drawn something other than the flat
   * background -- a reliable "is there actually a frame worth
   * capturing yet" signal. PNG byte size is *not* reliable for this:
   * antialiasing noise on an otherwise-empty frame can compress to a
   * similar size as one with real geometry. */
  hasContent: () => boolean;
}

const UNDEFORMED_COLOR = 0x8a93a3;
const DEFORMED_COLOR = 0xd14b3a;
const NODE_COLOR = 0x4a5568;
const BACKGROUND_RGB: [number, number, number] = [0xf6, 0xf3, 0xec];
const BACKGROUND_TOLERANCE = 15;

/** Imperative Three.js scene, not @react-three/fiber -- deliberately
 * minimal (docs/MASTER_PLAN.md: "Web-first 3D viewer; not source of
 * truth"), so this stays a thin rendering layer over the pure geometry
 * helpers in cem/geometry.ts rather than its own framework. */
export const SceneViewer = forwardRef<SceneViewerHandle, SceneViewerProps>(function SceneViewer(
  { model, results, scale },
  ref,
) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const sceneRef = useRef<THREE.Scene | null>(null);
  const groupRef = useRef<THREE.Group | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const controlsRef = useRef<OrbitControls | null>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);

  useImperativeHandle(ref, () => ({
    capture: () => rendererRef.current?.domElement.toDataURL("image/png") ?? null,
    hasContent: () => {
      const canvas = rendererRef.current?.domElement;
      if (!canvas) return false;
      const probe = document.createElement("canvas");
      probe.width = 32;
      probe.height = 32;
      const ctx = probe.getContext("2d");
      if (!ctx) return false;
      ctx.drawImage(canvas, 0, 0, 32, 32);
      const data = ctx.getImageData(0, 0, 32, 32).data;
      for (let i = 0; i < data.length; i += 4) {
        const deviates = [0, 1, 2].some(
          (c) => Math.abs(data[i + c] - BACKGROUND_RGB[c]) > BACKGROUND_TOLERANCE,
        );
        if (deviates) return true;
      }
      return false;
    },
  }));

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

    // preserveDrawingBuffer: toDataURL() on a WebGL canvas can otherwise
    // return a blank frame, since browsers are free to clear the buffer
    // right after compositing.
    const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
    renderer.setPixelRatio(window.devicePixelRatio);
    renderer.setSize(container.clientWidth, container.clientHeight);
    container.appendChild(renderer.domElement);
    rendererRef.current = renderer;

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
      rendererRef.current = null;
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
});

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
