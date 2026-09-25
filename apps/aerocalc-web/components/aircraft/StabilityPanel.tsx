"use client";

import { AlertCircle, CheckCircle2, AlertTriangle } from "lucide-react";
import { BarChart, Bar, XAxis, ResponsiveContainer, ReferenceLine } from "recharts";
import styles from "./StabilityPanel.module.css";
import type { StabilityResult } from "../../lib/types";

function ClassificationIcon({ classification }: { classification: string }) {
  if (classification === "stable") return <CheckCircle2 size={16} className={styles.iconStable} />;
  if (classification === "marginal" || classification === "stable_sluggish")
    return <AlertTriangle size={16} className={styles.iconMarginal} />;
  return <AlertCircle size={16} className={styles.iconUnstable} />;
}

function StatRow({
  label, value, unit, classification,
}: { label: string; value: number; unit: string; classification?: string }) {
  return (
    <div className={styles.statRow}>
      <span>{label}</span>
      <span className={styles.statValue}>
        {value.toFixed(3)} {unit}
        {classification && <ClassificationIcon classification={classification} />}
      </span>
    </div>
  );
}

export default function StabilityPanel({ stability }: { stability: StabilityResult }) {
  const cgVsNpData = [
    { name: "MAC", np: stability.neutral_point_mac * 100 },
  ];

  return (
    <div className={styles.container}>
      <p className={styles.heading}>Static Stability Analysis</p>

      {stability.warnings.length > 0 && (
        <ul className={styles.warnings}>
          {stability.warnings.map((w, i) => (
            <li key={i} className={styles.warningItem}>
              <AlertTriangle size={14} /> {w}
            </li>
          ))}
        </ul>
      )}

      <div className={styles.section}>
        <p className={styles.sectionTitle}>Longitudinal</p>
        <StatRow label="Neutral Point" value={stability.neutral_point_mac * 100} unit="% MAC" />
        <StatRow label="CG Position" value={stability.cg_mac * 100} unit="% MAC" />
        <StatRow
          label="Static Margin"
          value={stability.static_margin_percent}
          unit="%"
          classification={stability.static_margin_classification}
        />
        <StatRow label="Cm-alpha" value={stability.cm_alpha} unit="/rad" />
        {stability.tail_volume_coefficient !== null && (
          <StatRow label="Tail Volume Coefficient" value={stability.tail_volume_coefficient} unit="" />
        )}
      </div>

      <div className={styles.chartWrapper} title="Neutral point (blue bar) vs CG (orange line) along the wing MAC, 0-100%">
        <ResponsiveContainer width="100%" height={80}>
          <BarChart layout="vertical" data={cgVsNpData} margin={{ top: 8, right: 8, left: 8, bottom: 8 }}>
            <XAxis type="number" domain={[0, 100]} hide />
            <Bar dataKey="np" fill="#38bdf8" barSize={12} />
            <ReferenceLine x={stability.cg_mac * 100} stroke="#f97316" strokeWidth={2} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className={styles.section}>
        <p className={styles.sectionTitle}>Lateral</p>
        <StatRow
          label="Cl-beta (dihedral effect)"
          value={stability.cl_beta}
          unit="/rad"
          classification={stability.cl_beta_classification}
        />
      </div>

      <div className={styles.section}>
        <p className={styles.sectionTitle}>Directional</p>
        <StatRow
          label="Cn-beta (weathercock)"
          value={stability.cn_beta}
          unit="/rad"
          classification={stability.cn_beta_classification}
        />
        {stability.vertical_tail_volume_coefficient !== null && (
          <StatRow label="Vertical Tail Volume Coefficient" value={stability.vertical_tail_volume_coefficient} unit="" />
        )}
      </div>
    </div>
  );
}
