"use client";

import { Canvas } from "@react-three/fiber";
import { OrbitControls, Line } from "@react-three/drei";
import styles from "./Blueprint3D.module.css";
import type { AircraftGeometry, SurfaceGeometry } from "../../lib/types";

// AircraftGeometry vertices are [x(aft), y(starboard), z(up)]. Three.js
// uses [x(right), y(up), z(toward viewer)], so we map aircraft (x,y,z) ->
// three (x, z, y): aft along three's x-axis, up stays up, spanwise along
// three's z-axis.
function toThreeCoords(v: number[]): [number, number, number] {
  return [v[0]!, v[2]!, v[1]!];
}

function SurfaceWireframe({ geometry, color }: { geometry: SurfaceGeometry; color: string }) {
  return (
    <>
      {geometry.edges.map(([a, b], i) => {
        const start = geometry.vertices[a!];
        const end = geometry.vertices[b!];
        if (!start || !end) return null;
        return (
          <Line
            key={i}
            points={[toThreeCoords(start), toThreeCoords(end)]}
            color={color}
            lineWidth={1.5}
          />
        );
      })}
    </>
  );
}

export default function Blueprint3D({ geometry }: { geometry: AircraftGeometry }) {
  const surfaces: { geom: SurfaceGeometry; color: string }[] = [
    { geom: geometry.wing, color: "#7dd3fc" },
    ...(geometry.horizontal_tail ? [{ geom: geometry.horizontal_tail, color: "#38bdf8" }] : []),
    ...(geometry.vertical_tail ? [{ geom: geometry.vertical_tail, color: "#38bdf8" }] : []),
    ...(geometry.canard ? [{ geom: geometry.canard, color: "#a78bfa" }] : []),
    ...(geometry.v_tail ? [{ geom: geometry.v_tail, color: "#38bdf8" }] : []),
    { geom: geometry.fuselage, color: "#94a3b8" },
  ];

  return (
    <div className={styles.container}>
      <p className={styles.heading}>3D Wireframe</p>
      <div className={styles.canvasWrapper}>
        <Canvas camera={{ position: [8, 4, 8], fov: 45 }}>
          <ambientLight intensity={0.6} />
          <directionalLight position={[5, 5, 5]} intensity={0.8} />
          {surfaces.map((s, i) => (
            <SurfaceWireframe key={i} geometry={s.geom} color={s.color} />
          ))}
          <OrbitControls enableDamping />
        </Canvas>
      </div>
    </div>
  );
}
