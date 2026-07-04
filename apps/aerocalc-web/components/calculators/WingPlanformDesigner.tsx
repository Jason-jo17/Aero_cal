"use client";

import { useState } from "react";
import styles from "./WingPlanformDesigner.module.css";

interface PlanformResults {
  taper_ratio: number;
  area: number;
  aspect_ratio: number;
  mac: number;
  y_mac: number;
  x_mac_le: number;
}

export default function WingPlanformDesigner() {
  const [span, setSpan] = useState<number>(10);
  const [rootChord, setRootChord] = useState<number>(2);
  const [tipChord, setTipChord] = useState<number>(1);
  const [sweep, setSweep] = useState<number>(15);
  
  const [results, setResults] = useState<PlanformResults | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleCalculate = async () => {
    setLoading(true);
    setError("");
    
    try {
      const baseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const response = await fetch(`${baseUrl}/aero/wing-planform`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          span: span,
          root_chord: rootChord,
          tip_chord: tipChord,
          sweep_angle_deg: sweep
        }),
      });

      if (!response.ok) {
        throw new Error("Failed to calculate planform properties");
      }

      const data = await response.json();
      setResults(data);
    } catch (err: any) {
      setError(err.message || "An error occurred");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={styles.container}>
      <div className={styles.controls}>
        <div className={styles.field}>
          <label htmlFor="span" className={styles.label}>Wingspan (m)</label>
          <input
            id="span"
            type="number"
            value={span}
            onChange={(e) => setSpan(Number(e.target.value))}
            className={styles.input}
            min={0.1}
            step={0.1}
            title="Total wing span from tip to tip"
            placeholder="e.g. 10.0"
          />
        </div>
        
        <div className={styles.field}>
          <label htmlFor="rootChord" className={styles.label}>Root Chord (m)</label>
          <input
            id="rootChord"
            type="number"
            value={rootChord}
            onChange={(e) => setRootChord(Number(e.target.value))}
            className={styles.input}
            min={0.01}
            step={0.1}
            title="Chord length at the centerline"
            placeholder="e.g. 2.0"
          />
        </div>
        
        <div className={styles.field}>
          <label htmlFor="tipChord" className={styles.label}>Tip Chord (m)</label>
          <input
            id="tipChord"
            type="number"
            value={tipChord}
            onChange={(e) => setTipChord(Number(e.target.value))}
            className={styles.input}
            min={0}
            step={0.1}
            title="Chord length at the wing tip"
            placeholder="e.g. 1.0"
          />
        </div>
        
        <div className={styles.field}>
          <label htmlFor="sweep" className={styles.label}>Sweep Angle (deg)</label>
          <input
            id="sweep"
            type="number"
            value={sweep}
            onChange={(e) => setSweep(Number(e.target.value))}
            className={styles.input}
            min={-45}
            max={75}
            step={1}
            title="Leading edge sweep angle in degrees"
            placeholder="e.g. 15"
          />
        </div>

        {error && <div className={styles.error}>{error}</div>}

        <button 
          onClick={handleCalculate} 
          disabled={loading}
          className={styles.button}
        >
          {loading ? "Calculating..." : "Calculate Planform"}
        </button>
      </div>

      {results && (
        <div className={styles.resultsGrid}>
          <div className={styles.resultCard}>
            <span className={styles.resultLabel}>Wing Area (S)</span>
            <span className={styles.resultValue}>{results.area.toFixed(2)} m²</span>
          </div>
          <div className={styles.resultCard}>
            <span className={styles.resultLabel}>Aspect Ratio (AR)</span>
            <span className={styles.resultValue}>{results.aspect_ratio.toFixed(2)}</span>
          </div>
          <div className={styles.resultCard}>
            <span className={styles.resultLabel}>Taper Ratio (λ)</span>
            <span className={styles.resultValue}>{results.taper_ratio.toFixed(2)}</span>
          </div>
          <div className={styles.resultCard}>
            <span className={styles.resultLabel}>Mean Aerodynamic Chord (MAC)</span>
            <span className={styles.resultValue}>{results.mac.toFixed(3)} m</span>
          </div>
          <div className={styles.resultCard}>
            <span className={styles.resultLabel}>Y-position of MAC</span>
            <span className={styles.resultValue}>{results.y_mac.toFixed(3)} m</span>
          </div>
          <div className={styles.resultCard}>
            <span className={styles.resultLabel}>MAC Leading Edge (X-offset)</span>
            <span className={styles.resultValue}>{results.x_mac_le.toFixed(3)} m</span>
          </div>
        </div>
      )}
    </div>
  );
}
