"use client";

import styles from "./BlueprintView.module.css";
import type { AircraftGeometry, SurfaceGeometry } from "../../lib/types";

type ViewKey = "top_view" | "front_view" | "side_view";

function pointsToPath(points: number[][], negateSecond: boolean): string {
  if (points.length === 0) return "";
  const commands = points.map((p, i) => {
    const y = negateSecond ? -p[1]! : p[1]!;
    return `${i === 0 ? "M" : "L"} ${p[0]!.toFixed(3)} ${y.toFixed(3)}`;
  });
  return commands.join(" ") + " Z";
}

function allSurfaces(geometry: AircraftGeometry): SurfaceGeometry[] {
  return [
    geometry.wing,
    geometry.horizontal_tail,
    geometry.vertical_tail,
    geometry.canard,
    geometry.v_tail,
    geometry.fuselage,
  ].filter((s): s is SurfaceGeometry => s !== null);
}

function ViewPanel({
  title, geometry, view, negateSecond,
}: { title: string; geometry: AircraftGeometry; view: ViewKey; negateSecond: boolean }) {
  const surfaces = allSurfaces(geometry).filter((s) => s[view].length > 0);
  const allPoints = surfaces.flatMap((s) => s[view]);

  if (allPoints.length === 0) {
    return (
      <div className={styles.panel}>
        <p className={styles.panelTitle}>{title}</p>
      </div>
    );
  }

  const xs = allPoints.map((p) => p[0]!);
  const ys = allPoints.map((p) => (negateSecond ? -p[1]! : p[1]!));
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);
  const padX = Math.max((maxX - minX) * 0.15, 0.3);
  const padY = Math.max((maxY - minY) * 0.15, 0.3);
  const viewBox = `${minX - padX} ${minY - padY} ${maxX - minX + padX * 2} ${maxY - minY + padY * 2}`;

  return (
    <div className={styles.panel}>
      <p className={styles.panelTitle}>{title}</p>
      <svg className={styles.svg} viewBox={viewBox} preserveAspectRatio="xMidYMid meet">
        {surfaces.map((s, i) => (
          <path key={i} d={pointsToPath(s[view], negateSecond)} className={styles.outline} />
        ))}
      </svg>
    </div>
  );
}

export default function BlueprintView({ geometry }: { geometry: AircraftGeometry }) {
  const wingSpan = geometry.wing.planform?.span ?? 0;
  const wingMac = geometry.wing.planform?.mac ?? 0;
  const fuselageLength = geometry.fuselage.side_view.reduce((max, p) => Math.max(max, p[0]!), 0);

  return (
    <div className={styles.container}>
      <p className={styles.heading}>Blueprint — Three View</p>
      <div className={styles.dimensions}>
        <span>Span: {wingSpan.toFixed(2)} m</span>
        <span>MAC: {wingMac.toFixed(2)} m</span>
        <span>Length: {fuselageLength.toFixed(2)} m</span>
      </div>
      <div className={styles.grid}>
        <ViewPanel title="Top View" geometry={geometry} view="top_view" negateSecond={false} />
        <ViewPanel title="Front View" geometry={geometry} view="front_view" negateSecond={true} />
        <ViewPanel title="Side View" geometry={geometry} view="side_view" negateSecond={true} />
      </div>
    </div>
  );
}
