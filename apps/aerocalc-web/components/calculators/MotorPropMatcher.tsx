"use client";

import { useState } from "react";
import styles from "./MotorPropMatcher.module.css";

interface PropulsionResults {
  motor_kv: number;
  voltage: number;
  prop_diameter_in: number;
  prop_pitch_in: number;
  rpm_no_load: number;
  rpm_loaded: number;
  thrust_grams: number;
  power_watts: number;
  current_amps: number;
  pitch_speed_ms: number;
}

export default function MotorPropMatcher() {
  const [kv, setKv] = useState<number>(2300);
  const [voltage, setVoltage] = useState<number>(14.8);
  const [diameter, setDiameter] = useState<number>(5.0);
  const [pitch, setPitch] = useState<number>(4.5);
  
  const [results, setResults] = useState<PropulsionResults | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleCalculate = async () => {
    setLoading(true);
    setError("");
    
    try {
      const baseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const response = await fetch(`${baseUrl}/propulsion/motor-prop-match`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          motor_kv: kv,
          voltage: voltage,
          prop_diameter_in: diameter,
          prop_pitch_in: pitch
        }),
      });

      if (!response.ok) {
        throw new Error("Failed to calculate propulsion properties");
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
          <label htmlFor="kv" className={styles.label}>Motor KV (RPM/V)</label>
          <input
            id="kv"
            type="number"
            value={kv}
            onChange={(e) => setKv(Number(e.target.value))}
            className={styles.input}
            min={100}
            step={50}
            title="Motor RPM per Volt"
            placeholder="e.g. 2300"
          />
        </div>
        
        <div className={styles.field}>
          <label htmlFor="voltage" className={styles.label}>Voltage (V)</label>
          <input
            id="voltage"
            type="number"
            value={voltage}
            onChange={(e) => setVoltage(Number(e.target.value))}
            className={styles.input}
            min={3.7}
            step={0.1}
            title="Battery voltage (e.g. 4S = 14.8V)"
            placeholder="e.g. 14.8"
          />
        </div>
        
        <div className={styles.field}>
          <label htmlFor="diameter" className={styles.label}>Prop Diameter (in)</label>
          <input
            id="diameter"
            type="number"
            value={diameter}
            onChange={(e) => setDiameter(Number(e.target.value))}
            className={styles.input}
            min={1}
            step={0.5}
            title="Propeller diameter in inches"
            placeholder="e.g. 5.0"
          />
        </div>
        
        <div className={styles.field}>
          <label htmlFor="pitch" className={styles.label}>Prop Pitch (in)</label>
          <input
            id="pitch"
            type="number"
            value={pitch}
            onChange={(e) => setPitch(Number(e.target.value))}
            className={styles.input}
            min={1}
            step={0.5}
            title="Propeller pitch in inches"
            placeholder="e.g. 4.5"
          />
        </div>

        {error && <div className={styles.error}>{error}</div>}

        <button 
          onClick={handleCalculate} 
          disabled={loading}
          className={styles.button}
        >
          {loading ? "Calculating..." : "Match Motor & Prop"}
        </button>
      </div>

      {results && (
        <div className={styles.resultsGrid}>
          <div className={styles.resultCard}>
            <span className={styles.resultLabel}>Static Thrust</span>
            <span className={styles.resultValue}>
              {results.thrust_grams > 1000 
                ? `${(results.thrust_grams / 1000).toFixed(2)} kg` 
                : `${results.thrust_grams.toFixed(0)} g`}
            </span>
          </div>
          <div className={styles.resultCard}>
            <span className={styles.resultLabel}>Loaded RPM</span>
            <span className={styles.resultValue}>{results.rpm_loaded.toFixed(0)} RPM</span>
          </div>
          <div className={styles.resultCard}>
            <span className={styles.resultLabel}>Power Absorbed</span>
            <span className={styles.resultValue}>{results.power_watts.toFixed(1)} W</span>
          </div>
          <div className={styles.resultCard}>
            <span className={styles.resultLabel}>Current Draw</span>
            <span className={styles.resultValue}>{results.current_amps.toFixed(1)} A</span>
          </div>
          <div className={styles.resultCard}>
            <span className={styles.resultLabel}>Pitch Speed</span>
            <span className={styles.resultValue}>{results.pitch_speed_ms.toFixed(1)} m/s</span>
          </div>
          <div className={styles.resultCard}>
            <span className={styles.resultLabel}>Efficiency (Thrust/Power)</span>
            <span className={styles.resultValue}>{(results.thrust_grams / results.power_watts).toFixed(2)} g/W</span>
          </div>
        </div>
      )}
    </div>
  );
}
