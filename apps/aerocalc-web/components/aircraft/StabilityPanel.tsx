"use client";

import { AlertCircle, CheckCircle2, AlertTriangle, Info } from "lucide-react";
import { BarChart, Bar, XAxis, YAxis, ResponsiveContainer, ReferenceLine } from "recharts";
import styles from "./StabilityPanel.module.css";
import type { StabilityResult } from "../../lib/types";

// Design spec §9 "Known Limitations" - always shown, not conditional on
// the backend's per-config warnings array, so a "boring" config that
// triggers zero warnings still discloses the tool's fidelity limits.
const MODEL_LIMITATIONS = [
  "No fuselage aerodynamic contribution to directional stability",
  "No sidewash modeled",
  "Incompressible flow only (no compressibility correction)",
  "Static analysis only (no dynamic modes)",
  "Single vertical tail only",
  "Fuselage is visual-only, not a lifting/moment-contributing body",
];

function ClassificationIcon({ classification }: { classification: string }) {
  if (classification === "stable") return <CheckCircle2 size={16} className={styles.iconStable} />;
  if (classification === "marginal" || classification === "stable_sluggish")
    return <AlertTriangle size={16} className={styles.iconMarginal} />;
  return <AlertCircle size={16} className={styles.iconUnstable} />;
}

function StatRow({
  label, value, unit, classification, title,
}: { label: string; value: number; unit: string; classification?: string; title?: string }) {
  return (
    <div className={styles.statRow} title={title}>
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
        <StatRow
          label="Neutral Point"
          value={stability.neutral_point_mac * 100}
          unit="% MAC"
          title="h_n = h_ac_wing + (tail contribution), Roskam Part VI / Raymer Ch. 16"
        />
        <StatRow
          label="CG Position"
          value={stability.cg_mac * 100}
          unit="% MAC"
          title="Fraction of wing MAC from its leading edge"
        />
        <StatRow
          label="Static Margin"
          value={stability.static_margin_percent}
          unit="%"
          classification={stability.static_margin_classification}
          title="Neutral point minus CG position, as %MAC"
        />
        <StatRow
          label="Cm-alpha"
          value={stability.cm_alpha}
          unit="/rad"
          title="-CL_alpha_wing x static margin, per radian"
        />
        {stability.tail_volume_coefficient !== null && (
          <StatRow
            label="Tail Volume Coefficient"
            value={stability.tail_volume_coefficient}
            unit=""
            title="(S_tail x moment arm) / (S_wing x MAC_wing)"
          />
        )}
      </div>

      <div className={styles.chartWrapper} title="Neutral point (blue bar) vs CG (orange line) along the wing MAC, 0-100%">
        <ResponsiveContainer width="100%" height={80}>
          <BarChart layout="vertical" data={cgVsNpData} margin={{ top: 8, right: 8, left: 8, bottom: 8 }}>
            <XAxis type="number" domain={[0, 100]} hide />
            <YAxis type="category" dataKey="name" hide />
            <Bar dataKey="np" fill="#38bdf8" barSize={12} />
            <ReferenceLine x={stability.cg_mac * 100} stroke="#f97316" strokeWidth={2} ifOverflow="extendDomain" />
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
          title="Dihedral effect: direct-dihedral + wing-sweep contributions (rule-of-thumb estimates)"
        />
      </div>

      <div className={styles.section}>
        <p className={styles.sectionTitle}>Directional</p>
        <StatRow
          label="Cn-beta (weathercock)"
          value={stability.cn_beta}
          unit="/rad"
          classification={stability.cn_beta_classification}
          title="Weathercock stability from vertical tail volume coefficient"
        />
        {stability.vertical_tail_volume_coefficient !== null && (
          <StatRow
            label="Vertical Tail Volume Coefficient"
            value={stability.vertical_tail_volume_coefficient}
            unit=""
            title="(S_vtail x moment arm) / (S_wing x span)"
          />
        )}
      </div>

      <div className={styles.section}>
        <p className={styles.sectionTitle}>Model Limitations</p>
        <ul className={styles.limitations}>
          {MODEL_LIMITATIONS.map((limitation) => (
            <li key={limitation} className={styles.limitationItem}>
              <Info size={14} /> {limitation}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
