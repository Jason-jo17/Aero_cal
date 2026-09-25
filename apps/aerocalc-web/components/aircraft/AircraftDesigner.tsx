"use client";

import { useState } from "react";
import dynamic from "next/dynamic";
import styles from "./AircraftDesigner.module.css";
import BlueprintView from "./BlueprintView";
import StabilityPanel from "./StabilityPanel";
import type {
  AircraftConfig,
  AircraftConfigurationType,
  AircraftSurface,
  AircraftVerticalTail,
  AircraftVTail,
  AircraftFuselage,
  AircraftMassProperties,
  AircraftDesignResponse,
} from "../../lib/types";

// Blueprint3D uses @react-three/fiber's WebGL Canvas, which cannot be
// server-rendered; load it client-only, matching the flight simulator's
// dynamic-import pattern in app/page.tsx.
const Blueprint3D = dynamic(() => import("./Blueprint3D"), {
  ssr: false,
  loading: () => <div className={styles.simLoading}>Loading 3D view…</div>,
});

const DEFAULT_WING: AircraftSurface = {
  span: 10.0, root_chord: 1.5, tip_chord: 1.0, sweep_deg: 0, dihedral_deg: 5,
  x_position: 2.0, z_position: 0,
};
const DEFAULT_HTAIL: AircraftSurface = {
  span: 3.0, root_chord: 0.8, tip_chord: 0.5, sweep_deg: 5,
  x_position: 6.0, z_position: 0.5,
};
const DEFAULT_VTAIL_FIN: AircraftVerticalTail = {
  height: 1.2, root_chord: 0.9, tip_chord: 0.5, sweep_deg: 15,
  x_position: 6.2, z_position: 0.2,
};
const DEFAULT_CANARD: AircraftSurface = {
  span: 2.0, root_chord: 0.6, tip_chord: 0.4, sweep_deg: 0,
  x_position: 0.5, z_position: 0,
};
const DEFAULT_V_TAIL: AircraftVTail = {
  span: 2.5, root_chord: 0.9, tip_chord: 0.5, dihedral_v_deg: 40, sweep_deg: 10,
  x_position: 6.2, z_position: 0.4,
};
const DEFAULT_FUSELAGE: AircraftFuselage = {
  length: 7.5, max_width: 1.1, max_height: 1.3, nose_length: 1.2, tail_length: 1.8,
};
const DEFAULT_MASS: AircraftMassProperties = {
  mass_kg: 900, cg_x_position: 2.5, cruise_speed_ms: 55,
};

function defaultConfigFor(type: AircraftConfigurationType): AircraftConfig {
  const base: AircraftConfig = {
    configuration_type: type,
    wing: { ...DEFAULT_WING },
    fuselage: { ...DEFAULT_FUSELAGE },
    mass: { ...DEFAULT_MASS },
  };
  if (type === "conventional" || type === "t_tail") {
    base.horizontal_tail = { ...DEFAULT_HTAIL };
    base.vertical_tail = { ...DEFAULT_VTAIL_FIN };
  } else if (type === "canard") {
    base.canard = { ...DEFAULT_CANARD };
    base.vertical_tail = { ...DEFAULT_VTAIL_FIN };
  } else if (type === "v_tail") {
    base.v_tail = { ...DEFAULT_V_TAIL };
  }
  return base;
}

function NumberField({
  label, value, onChange, step = 0.1, min,
}: { label: string; value: number; onChange: (v: number) => void; step?: number; min?: number }) {
  return (
    <div className={styles.field}>
      <label className={styles.label}>{label}</label>
      <input
        type="number"
        className={styles.input}
        value={value}
        step={step}
        min={min}
        title={label}
        onChange={(e) => onChange(Number(e.target.value))}
      />
    </div>
  );
}

export default function AircraftDesigner() {
  const [configType, setConfigType] = useState<AircraftConfigurationType>("conventional");
  const [config, setConfig] = useState<AircraftConfig>(() => defaultConfigFor("conventional"));
  const [results, setResults] = useState<AircraftDesignResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleTypeChange = (type: AircraftConfigurationType) => {
    setConfigType(type);
    setConfig(defaultConfigFor(type));
    setResults(null);
  };

  const updateWing = (patch: Partial<AircraftSurface>) =>
    setConfig((prev) => ({ ...prev, wing: { ...prev.wing, ...patch } }));

  const updateHorizontalTail = (patch: Partial<AircraftSurface>) =>
    setConfig((prev) => ({ ...prev, horizontal_tail: { ...(prev.horizontal_tail as AircraftSurface), ...patch } }));

  const updateCanard = (patch: Partial<AircraftSurface>) =>
    setConfig((prev) => ({ ...prev, canard: { ...(prev.canard as AircraftSurface), ...patch } }));

  const updateVerticalTail = (patch: Partial<AircraftVerticalTail>) =>
    setConfig((prev) => ({ ...prev, vertical_tail: { ...(prev.vertical_tail as AircraftVerticalTail), ...patch } }));

  const updateVTail = (patch: Partial<AircraftVTail>) =>
    setConfig((prev) => ({ ...prev, v_tail: { ...(prev.v_tail as AircraftVTail), ...patch } }));

  const updateFuselage = (patch: Partial<AircraftFuselage>) =>
    setConfig((prev) => ({ ...prev, fuselage: { ...prev.fuselage, ...patch } }));

  const updateMass = (patch: Partial<AircraftMassProperties>) =>
    setConfig((prev) => ({ ...prev, mass: { ...prev.mass, ...patch } }));

  const handleCalculate = async () => {
    setLoading(true);
    setError("");
    try {
      if (config.mass.cg_x_position < 0 || config.mass.cg_x_position > config.fuselage.length) {
        throw new Error("CG position should be within the fuselage length");
      }
      const baseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const response = await fetch(`${baseUrl}/aircraft/design`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(config),
      });
      if (!response.ok) {
        const detail = await response.json().catch(() => null);
        throw new Error(
          detail?.detail ? String(detail.detail) : "Failed to calculate aircraft design"
        );
      }
      const data: AircraftDesignResponse = await response.json();
      setResults(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "An error occurred");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={styles.container}>
      <div className={styles.controls}>
        <div className={styles.field}>
          <label className={styles.label} htmlFor="configType">Configuration Type</label>
          <select
            id="configType"
            className={styles.input}
            value={configType}
            onChange={(e) => handleTypeChange(e.target.value as AircraftConfigurationType)}
          >
            <option value="conventional">Conventional</option>
            <option value="t_tail">T-Tail</option>
            <option value="canard">Canard</option>
            <option value="v_tail">V-Tail</option>
            <option value="flying_wing">Flying Wing / Tailless</option>
          </select>
        </div>

        <fieldset className={styles.fieldset}>
          <legend>Wing</legend>
          <NumberField label="Span (m)" value={config.wing.span} onChange={(v) => updateWing({ span: v })} />
          <NumberField label="Root Chord (m)" value={config.wing.root_chord} onChange={(v) => updateWing({ root_chord: v })} />
          <NumberField label="Tip Chord (m)" value={config.wing.tip_chord} onChange={(v) => updateWing({ tip_chord: v })} />
          <NumberField label="Sweep (deg)" value={config.wing.sweep_deg ?? 0} onChange={(v) => updateWing({ sweep_deg: v })} />
          <NumberField label="Dihedral (deg)" value={config.wing.dihedral_deg ?? 0} onChange={(v) => updateWing({ dihedral_deg: v })} />
          <NumberField label="X Position (m from nose)" value={config.wing.x_position} onChange={(v) => updateWing({ x_position: v })} />
        </fieldset>

        {(configType === "conventional" || configType === "t_tail") && config.horizontal_tail && (
          <fieldset className={styles.fieldset}>
            <legend>Horizontal Tail</legend>
            <NumberField label="Span (m)" value={config.horizontal_tail.span} onChange={(v) => updateHorizontalTail({ span: v })} />
            <NumberField label="Root Chord (m)" value={config.horizontal_tail.root_chord} onChange={(v) => updateHorizontalTail({ root_chord: v })} />
            <NumberField label="Tip Chord (m)" value={config.horizontal_tail.tip_chord} onChange={(v) => updateHorizontalTail({ tip_chord: v })} />
            <NumberField label="X Position (m from nose)" value={config.horizontal_tail.x_position} onChange={(v) => updateHorizontalTail({ x_position: v })} />
            <NumberField label="Z Position (m)" value={config.horizontal_tail.z_position ?? 0} onChange={(v) => updateHorizontalTail({ z_position: v })} />
          </fieldset>
        )}

        {configType === "canard" && config.canard && (
          <fieldset className={styles.fieldset}>
            <legend>Canard</legend>
            <NumberField label="Span (m)" value={config.canard.span} onChange={(v) => updateCanard({ span: v })} />
            <NumberField label="Root Chord (m)" value={config.canard.root_chord} onChange={(v) => updateCanard({ root_chord: v })} />
            <NumberField label="Tip Chord (m)" value={config.canard.tip_chord} onChange={(v) => updateCanard({ tip_chord: v })} />
            <NumberField label="X Position (m from nose)" value={config.canard.x_position} onChange={(v) => updateCanard({ x_position: v })} />
          </fieldset>
        )}

        {(configType === "conventional" || configType === "t_tail" || configType === "canard") && config.vertical_tail && (
          <fieldset className={styles.fieldset}>
            <legend>Vertical Tail</legend>
            <NumberField label="Height (m)" value={config.vertical_tail.height} onChange={(v) => updateVerticalTail({ height: v })} />
            <NumberField label="Root Chord (m)" value={config.vertical_tail.root_chord} onChange={(v) => updateVerticalTail({ root_chord: v })} />
            <NumberField label="Tip Chord (m)" value={config.vertical_tail.tip_chord} onChange={(v) => updateVerticalTail({ tip_chord: v })} />
            <NumberField label="X Position (m from nose)" value={config.vertical_tail.x_position} onChange={(v) => updateVerticalTail({ x_position: v })} />
          </fieldset>
        )}

        {configType === "v_tail" && config.v_tail && (
          <fieldset className={styles.fieldset}>
            <legend>V-Tail</legend>
            <NumberField label="Span (m)" value={config.v_tail.span} onChange={(v) => updateVTail({ span: v })} />
            <NumberField label="Root Chord (m)" value={config.v_tail.root_chord} onChange={(v) => updateVTail({ root_chord: v })} />
            <NumberField label="Tip Chord (m)" value={config.v_tail.tip_chord} onChange={(v) => updateVTail({ tip_chord: v })} />
            <NumberField label="Dihedral Angle (deg)" value={config.v_tail.dihedral_v_deg} onChange={(v) => updateVTail({ dihedral_v_deg: v })} min={0} />
            <NumberField label="X Position (m from nose)" value={config.v_tail.x_position} onChange={(v) => updateVTail({ x_position: v })} />
          </fieldset>
        )}

        <fieldset className={styles.fieldset}>
          <legend>Fuselage</legend>
          <NumberField label="Length (m)" value={config.fuselage.length} onChange={(v) => updateFuselage({ length: v })} />
          <NumberField label="Max Width (m)" value={config.fuselage.max_width} onChange={(v) => updateFuselage({ max_width: v })} />
          <NumberField label="Max Height (m)" value={config.fuselage.max_height} onChange={(v) => updateFuselage({ max_height: v })} />
          <NumberField label="Nose Length (m)" value={config.fuselage.nose_length} onChange={(v) => updateFuselage({ nose_length: v })} />
          <NumberField label="Tail Length (m)" value={config.fuselage.tail_length} onChange={(v) => updateFuselage({ tail_length: v })} />
        </fieldset>

        <fieldset className={styles.fieldset}>
          <legend>Mass &amp; CG</legend>
          <NumberField label="Mass (kg)" value={config.mass.mass_kg} onChange={(v) => updateMass({ mass_kg: v })} />
          <NumberField label="CG X Position (m from nose)" value={config.mass.cg_x_position} onChange={(v) => updateMass({ cg_x_position: v })} />
          <NumberField label="Cruise Speed (m/s)" value={config.mass.cruise_speed_ms} onChange={(v) => updateMass({ cruise_speed_ms: v })} />
        </fieldset>

        <button type="button" className={styles.button} onClick={handleCalculate} disabled={loading}>
          {loading ? "Calculating..." : "Calculate"}
        </button>
        {error && <p className={styles.error}>{error}</p>}
      </div>

      <div className={styles.viewsPanel}>
        {results ? (
          <>
            <BlueprintView geometry={results.geometry} />
            <Blueprint3D geometry={results.geometry} />
            <StabilityPanel stability={results.stability} />
          </>
        ) : (
          <p className={styles.placeholder}>
            Configure an aircraft and click Calculate to see the blueprint and stability analysis.
          </p>
        )}
      </div>
    </div>
  );
}
