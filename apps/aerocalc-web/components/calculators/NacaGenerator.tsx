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
  ReferenceLine,
} from "recharts";
import { Info } from "lucide-react";
import styles from "./NacaGenerator.module.css";

export default function NacaGenerator() {
  const [digits, setDigits] = useState("2412");
  const [airfoil, setAirfoil] = useState<{
    name: string;
    x_upper: number[];
    y_upper: number[];
    y_lower: number[];
  } | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchAirfoil = async () => {
    setLoading(true);
    setError(null);
    try {
      const baseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const res = await fetch(`${baseUrl}/aero/naca`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ digits, n_points: 100 }),
      });
      if (!res.ok) throw new Error("Failed to fetch airfoil data");
      const data = await res.json();
      setAirfoil(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  };

  const chartData = airfoil
    ? airfoil.x_upper.map((x: number, i: number) => ({
        x,
        upper: airfoil.y_upper[i],
        lower: airfoil.y_lower[i],
      }))
    : [];

  return (
    <div className={styles.container}>
      <h2 className={styles.heading}>NACA Airfoil Generator</h2>
      <p className={styles.subheading}>
        Generate classical NACA 4-digit airfoil cross-sections.
      </p>

      <div className={styles.formRow}>
        <div className={styles.fieldGroup}>
          <label htmlFor="naca-digits" className={styles.label}>
            NACA Digits
          </label>
          <input
            id="naca-digits"
            className={styles.input}
            value={digits}
            onChange={(e) => setDigits(e.target.value)}
            placeholder="e.g. 2412"
            title="NACA 4-digit airfoil code (e.g. 2412)"
          />
        </div>
        <button
          onClick={fetchAirfoil}
          disabled={loading || digits.length < 4}
          className={styles.generateBtn}
        >
          {loading ? "Computing…" : "Generate Profile"}
        </button>
      </div>

      {error && <div className={styles.error}>{error}</div>}

      {airfoil && (
        <div className={styles.card}>
          <div className={styles.cardHeader}>
            <h3 className={styles.cardTitle}>{airfoil.name} Cross-Section</h3>
            <div className={styles.cardMeta}>
              <span>Max Thickness: {Math.max(...airfoil.y_upper).toFixed(3)}</span>
              <span>Points: {airfoil.x_upper.length * 2}</span>
            </div>
          </div>

          <div className={styles.chartArea}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart
                data={chartData}
                margin={{ top: 20, right: 30, left: 20, bottom: 20 }}
              >
                <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
                <XAxis
                  dataKey="x"
                  type="number"
                  domain={[0, 1]}
                  tickCount={11}
                  label={{
                    value: "Chord (x/c)",
                    position: "insideBottom",
                    offset: -15,
                  }}
                />
                <YAxis
                  domain={[-0.3, 0.3]}
                  label={{
                    value: "Thickness (y/c)",
                    angle: -90,
                    position: "insideLeft",
                    offset: 10,
                  }}
                />
                <Tooltip />
                <ReferenceLine y={0} stroke="#000" strokeOpacity={0.3} />
                <Line
                  type="monotone"
                  dataKey="upper"
                  stroke="#2563eb"
                  strokeWidth={2}
                  dot={false}
                  isAnimationActive={false}
                />
                <Line
                  type="monotone"
                  dataKey="lower"
                  stroke="#2563eb"
                  strokeWidth={2}
                  dot={false}
                  isAnimationActive={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>

          <div className={styles.cardFooter}>
            <div className={styles.infoRow}>
              <Info size={20} className={styles.infoIcon} />
              <p className={styles.infoText}>
                The NACA 4-digit definition: first digit = max camber (% chord),
                second = position of max camber (tenths of chord), last two =
                max thickness (% chord).
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
