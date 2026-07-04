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
  Legend
} from "recharts";
import styles from "./PolarCurveGenerator.module.css";

interface PolarData {
  alpha: number;
  cl: number;
  cd: number;
  cm: number;
}

export default function PolarCurveGenerator() {
  const [camber, setCamber] = useState<number>(2);
  const [thickness, setThickness] = useState<number>(12);
  const [data, setData] = useState<PolarData[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleGenerate = async () => {
    setLoading(true);
    setError("");
    
    try {
      const baseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const response = await fetch(`${baseUrl}/aero/polar-curves`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          camber_percent: camber,
          thickness_percent: thickness,
          min_alpha: -10,
          max_alpha: 20
        }),
      });

      if (!response.ok) {
        throw new Error("Failed to generate polar curves");
      }

      const result = await response.json();
      
      // Transform data for Recharts
      const chartData = result.alpha.map((a: number, i: number) => ({
        alpha: a,
        cl: result.cl[i],
        cd: result.cd[i],
        cm: result.cm[i],
      }));
      
      setData(chartData);
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
          <label htmlFor="camber" className={styles.label}>Max Camber (%)</label>
          <input
            id="camber"
            type="number"
            value={camber}
            onChange={(e) => setCamber(Number(e.target.value))}
            className={styles.input}
            min={0}
            max={9}
            step={1}
            title="Maximum camber in percentage of chord"
            placeholder="e.g. 2"
          />
        </div>
        
        <div className={styles.field}>
          <label htmlFor="thickness" className={styles.label}>Thickness (%)</label>
          <input
            id="thickness"
            type="number"
            value={thickness}
            onChange={(e) => setThickness(Number(e.target.value))}
            className={styles.input}
            min={1}
            max={40}
            step={1}
            title="Maximum thickness in percentage of chord"
            placeholder="e.g. 12"
          />
        </div>

        {error && <div className={styles.error}>{error}</div>}

        <button 
          onClick={handleGenerate} 
          disabled={loading}
          className={styles.button}
        >
          {loading ? "Calculating..." : "Generate Polar Curves"}
        </button>
      </div>

      {data.length > 0 && (
        <>
          <div className={styles.chartContainer}>
            <h3 className={styles.chartTitle}>Lift Coefficient (Cl) vs Angle of Attack (α)</h3>
            <div className={styles.chartWrapper}>
              <ResponsiveContainer>
                <LineChart data={data} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis 
                    dataKey="alpha" 
                    label={{ value: 'Alpha (deg)', position: 'insideBottomRight', offset: -5 }} 
                    type="number" 
                    domain={['dataMin', 'dataMax']} 
                  />
                  <YAxis label={{ value: 'Cl', angle: -90, position: 'insideLeft' }} />
                  <Tooltip formatter={(val: any) => Number(val).toFixed(3)} />
                  <Line type="monotone" dataKey="cl" stroke="#3b82f6" dot={false} strokeWidth={2} name="Lift Coeff (Cl)" />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className={styles.chartContainer}>
            <h3 className={styles.chartTitle}>Drag Polar (Cd vs Cl)</h3>
            <div className={styles.chartWrapper}>
              <ResponsiveContainer>
                <LineChart data={data} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis 
                    dataKey="cl" 
                    label={{ value: 'Cl', position: 'insideBottomRight', offset: -5 }} 
                    type="number" 
                    domain={['dataMin', 'dataMax']} 
                  />
                  <YAxis label={{ value: 'Cd', angle: -90, position: 'insideLeft' }} />
                  <Tooltip formatter={(val: any) => Number(val).toFixed(4)} />
                  <Line type="monotone" dataKey="cd" stroke="#ef4444" dot={false} strokeWidth={2} name="Drag Coeff (Cd)" />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
