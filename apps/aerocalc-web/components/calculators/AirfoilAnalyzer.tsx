"use client";

import { useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  ReferenceLine
} from "recharts";
import { Info } from "lucide-react";
import styles from "./AirfoilAnalyzer.module.css";

export default function AirfoilAnalyzer() {
  const [digits, setDigits] = useState("2412");
  const [alpha, setAlpha] = useState<number>(5);
  const [reynolds, setReynolds] = useState<number>(1e6);
  const [results, setResults] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchAnalysis = async () => {
    setLoading(true);
    setError(null);
    try {
      const baseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const res = await fetch(`${baseUrl}/aero/airfoil-analysis`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          naca_digits: digits, 
          alpha_deg: alpha, 
          reynolds: reynolds 
        }),
      });
      
      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        throw new Error(errorData.detail || "Failed to analyze airfoil");
      }
      
      const data = await res.json();
      setResults(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  };

  const cpChartData = results?.x_cp?.map((x: number, i: number) => ({
    x,
    cp: -results.Cp[i], // Negative Cp is standard in aero plots
  })) || [];

  return (
    <div className={styles.container}>
      <h2 className={styles.heading}>Airfoil Analysis (Panel Method)</h2>
      <p className={styles.subheading}>
        Analyze lift, drag, and pressure distribution of NACA airfoils using an inviscid vortex panel method with empirical viscous drag estimation.
      </p>

      <div className={styles.controls}>
        <div className={styles.field}>
          <label htmlFor="digits" className={styles.label}>NACA 4-Digit Profile</label>
          <input
            id="digits"
            className={styles.input}
            value={digits}
            onChange={(e) => setDigits(e.target.value)}
            placeholder="e.g. 2412"
          />
        </div>
        
        <div className={styles.field}>
          <label htmlFor="alpha" className={styles.label}>Angle of Attack (°)</label>
          <input
            id="alpha"
            type="number"
            step="0.5"
            className={styles.input}
            value={alpha}
            onChange={(e) => setAlpha(Number(e.target.value))}
          />
        </div>
        
        <div className={styles.field}>
          <label htmlFor="reynolds" className={styles.label}>Reynolds Number</label>
          <input
            id="reynolds"
            type="number"
            step="100000"
            className={styles.input}
            value={reynolds}
            onChange={(e) => setReynolds(Number(e.target.value))}
          />
        </div>

        <button
          onClick={fetchAnalysis}
          disabled={loading || digits.length < 4}
          className={styles.button}
        >
          {loading ? "Analyzing…" : "Run Analysis"}
        </button>
      </div>

      {error && <div className={styles.error}>{error}</div>}

      {results && (
        <div className={styles.resultsWrapper}>
          <div className={styles.metricsGrid}>
            <div className={styles.metricCard}>
              <span className={styles.metricLabel}>Lift Coeff (Cl)</span>
              <span className={styles.metricValue}>{results.Cl.toFixed(4)}</span>
            </div>
            <div className={styles.metricCard}>
              <span className={styles.metricLabel}>Total Drag (Cd)</span>
              <span className={styles.metricValue}>{results.Cd_total.toFixed(4)}</span>
            </div>
            <div className={styles.metricCard}>
              <span className={styles.metricLabel}>L/D Ratio</span>
              <span className={styles.metricValue}>{results.L_D.toFixed(1)}</span>
            </div>
            <div className={styles.metricCard}>
              <span className={styles.metricLabel}>Moment Coeff (Cm)</span>
              <span className={styles.metricValue}>{results.Cm.toFixed(4)}</span>
            </div>
          </div>

          <div className={styles.chartContainer}>
            <h3 className={styles.chartTitle}>Pressure Coefficient (-Cp)</h3>
            <div className={styles.chartArea}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart
                  data={cpChartData}
                  margin={{ top: 20, right: 30, left: 20, bottom: 20 }}
                >
                  <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
                  <XAxis
                    dataKey="x"
                    type="number"
                    domain={[0, 1]}
                    tickCount={11}
                    label={{
                      value: "Chord Position (x/c)",
                      position: "insideBottom",
                      offset: -15,
                    }}
                  />
                  <YAxis
                    label={{
                      value: "-Cp",
                      angle: -90,
                      position: "insideLeft",
                      offset: 10,
                    }}
                  />
                  <Tooltip formatter={(value: any) => typeof value === 'number' ? value.toFixed(3) : value} />
                  <ReferenceLine y={0} stroke="#000" strokeOpacity={0.3} />
                  <Line
                    type="monotone"
                    dataKey="cp"
                    stroke="#ef4444"
                    strokeWidth={2}
                    dot={false}
                    isAnimationActive={false}
                    name="-Cp"
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
            <p className={styles.note}>
              <Info size={16} style={{display: 'inline', marginRight: '5px', verticalAlign: 'middle'}}/>
              Negative Cp is plotted upwards as is standard convention in aerodynamics.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
