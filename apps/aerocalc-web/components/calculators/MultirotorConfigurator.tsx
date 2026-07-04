"use client";

import { AlertCircle, CheckCircle2, Battery, Cpu, Activity, Zap, Sparkles, Bot } from "lucide-react";
import styles from "./MultirotorConfigurator.module.css";
import { useDroneConfig } from "../../contexts/DroneConfigContext";
import { DroneConfig } from "../../lib/types";
import { useState } from "react";

/** Reusable labelled number field */
function Field({
  id,
  label,
  name,
  value,
  unit,
  onChange,
}: {
  id: string;
  label: string;
  name: keyof DroneConfig;
  value: number;
  unit?: string;
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
}) {
  const displayLabel = unit ? `${label} (${unit})` : label;
  return (
    <div className={styles.fieldGroup}>
      <label htmlFor={id} className={styles.label}>
        {displayLabel}
      </label>
      <input
        id={id}
        name={name}
        type="number"
        value={value}
        onChange={onChange}
        placeholder={String(value)}
        title={displayLabel}
        className={styles.input}
      />
    </div>
  );
}

export default function MultirotorConfigurator() {
  const { config, setConfig, results, setResults } = useDroneConfig();
  const [loading, setLoading] = useState(false);

  const [aiGoal, setAiGoal] = useState("");
  const [aiLoading, setAiLoading] = useState(false);
  const [aiReasoning, setAiReasoning] = useState<string | null>(null);
  const [aiError, setAiError] = useState<string | null>(null);
  const [aiNotes, setAiNotes] = useState<string | null>(null);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setConfig({ ...config, [e.target.name]: parseFloat(e.target.value) || 0 });
  };

  const calculate = async () => {
    setLoading(true);
    try {
      const baseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const res = await fetch(`${baseUrl}/aero/multirotor`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(config),
      });
      const data = await res.json();
      setResults(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const designWithAi = async () => {
    if (!aiGoal.trim()) return;
    setAiLoading(true);
    setAiError(null);
    setAiReasoning(null);
    setAiNotes(null);
    try {
      const aiUrl = process.env.NEXT_PUBLIC_AI_AGENT_URL || "http://localhost:8001";
      const res = await fetch(`${aiUrl}/ai/solve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ goal: aiGoal, domain: "multirotor" }),
      });
      const data = await res.json();
      if (!res.ok || data.error) {
        setAiError(data.error || data.detail || "AI design request failed");
        return;
      }
      // AI only proposes the config; the real deterministic engine (already
      // run server-side by /ai/solve) produced simulated_results - both are
      // shown, but the numbers on screen always come from the physics engine.
      setConfig({ ...config, ...data.proposed_config });
      setResults(data.simulated_results ?? null);
      setAiReasoning(data.reasoning || null);
      setAiNotes(data.notes || null);
    } catch (err) {
      setAiError(err instanceof Error ? err.message : "AI design request failed");
    } finally {
      setAiLoading(false);
    }
  };

  return (
    <div className={styles.container}>
      <h2 className={styles.heading}>Multirotor Configurator</h2>
      <p className={styles.subheading}>
        Configure components to estimate flight performance.
      </p>

      <div className={styles.aiDesignBox}>
        <label htmlFor="ai-goal" className={`${styles.formPanelTitle} ${styles.aiDesignTitle}`}>
          <Bot size={18} /> Describe what you want, let AI configure it
        </label>
        <div className={styles.aiDesignRow}>
          <input
            id="ai-goal"
            type="text"
            value={aiGoal}
            onChange={(e) => setAiGoal(e.target.value)}
            placeholder="e.g. a drone that carries 500g for 20 minutes"
            className={`${styles.input} ${styles.aiDesignInput}`}
          />
          <button
            type="button"
            onClick={designWithAi}
            disabled={aiLoading || !aiGoal.trim()}
            className={styles.runBtn}
          >
            <Sparkles size={16} />
            {aiLoading ? "Designing…" : "Design with AI"}
          </button>
        </div>
        {aiError && <div className={styles.feedbackWarning}><AlertCircle size={16} /><p>{aiError}</p></div>}
        {aiReasoning && (
          <div className={`${styles.feedbackCard} ${styles.aiReasoningCard}`}>
            <div className={styles.feedbackCardBody}>
              <p className={`${styles.feedbackEmpty} ${styles.aiReasoningText}`}>{aiReasoning}</p>
              {aiNotes && <p className={`${styles.feedbackEmpty} ${styles.aiNotesText}`}>{aiNotes}</p>}
            </div>
          </div>
        )}
      </div>

      <div className={styles.layout}>
        {/* ── Configuration Form ── */}
        <div className={styles.formPanel}>
          <h3 className={styles.formPanelTitle}>Components</h3>

          <div className={styles.fieldsGrid}>
            <Field id="frame-size" label="Frame Size" name="frame_size" value={config.frame_size} unit="mm" onChange={handleChange} />
            <Field id="payload-weight" label="Payload" name="payload_weight" value={config.payload_weight} unit="g" onChange={handleChange} />

            <p className={styles.sectionLabel}>Motor &amp; Propeller</p>

            <Field id="motor-kv" label="Motor KV" name="motor_kv" value={config.motor_kv} onChange={handleChange} />
            <Field id="prop-diameter" label="Prop Diameter" name="prop_diameter" value={config.prop_diameter} unit="in" onChange={handleChange} />
            <Field id="motor-max-current" label="Max Current" name="motor_max_current" value={config.motor_max_current} unit="A" onChange={handleChange} />
            <Field id="prop-pitch" label="Prop Pitch" name="prop_pitch" value={config.prop_pitch} unit="in" onChange={handleChange} />

            <p className={styles.sectionLabel}>Battery</p>

            <Field id="battery-cells" label="Cells" name="battery_cells" value={config.battery_cells} unit="S" onChange={handleChange} />
            <Field id="battery-capacity" label="Capacity" name="battery_capacity" value={config.battery_capacity} unit="mAh" onChange={handleChange} />
            <Field id="battery-c-rating" label="C-Rating" name="battery_c_rating" value={config.battery_c_rating} onChange={handleChange} />
            <Field id="battery-weight" label="Bat. Weight" name="battery_weight" value={config.battery_weight} unit="g" onChange={handleChange} />
          </div>

          <button
            type="button"
            onClick={calculate}
            disabled={loading}
            className={styles.runBtn}
          >
            {loading ? "Calculating…" : "Run Analysis"}
          </button>
        </div>

        {/* ── Results Dashboard ── */}
        <div className={styles.resultsPanel}>
          {results ? (
            <>
              {/* KPI Cards */}
              <div className={styles.kpiGrid}>
                <div className={styles.kpiCard}>
                  <div className={`${styles.kpiIconWrap} ${styles.kpiIconWrapBlue}`}>
                    <Activity size={24} />
                  </div>
                  <div>
                    <p className={styles.kpiLabel}>Total Weight</p>
                    <p className={styles.kpiValue}>{results.total_weight_g.toFixed(0)} g</p>
                  </div>
                </div>

                <div className={styles.kpiCard}>
                  <div className={`${styles.kpiIconWrap} ${styles.kpiIconWrapYellow}`}>
                    <Zap size={24} />
                  </div>
                  <div>
                    <p className={styles.kpiLabel}>Thrust-to-Weight</p>
                    <p className={styles.kpiValue}>{results.thrust_to_weight_ratio.toFixed(2)} : 1</p>
                  </div>
                </div>

                <div className={styles.kpiCard}>
                  <div className={`${styles.kpiIconWrap} ${styles.kpiIconWrapGreen}`}>
                    <Battery size={24} />
                  </div>
                  <div>
                    <p className={styles.kpiLabel}>Hover Time</p>
                    <p className={styles.kpiValue}>{results.max_flight_time_min.toFixed(1)} min</p>
                  </div>
                </div>

                <div className={styles.kpiCard}>
                  <div className={`${styles.kpiIconWrap} ${styles.kpiIconWrapPurple}`}>
                    <Cpu size={24} />
                  </div>
                  <div>
                    <p className={styles.kpiLabel}>Hover Throttle</p>
                    <p className={styles.kpiValue}>{results.hover_throttle_percent.toFixed(1)} %</p>
                  </div>
                </div>
              </div>

              {/* Feedback */}
              <div className={styles.feedbackCard}>
                <div className={styles.feedbackCardHeader}>
                  <h3 className={styles.feedbackCardTitle}>Analysis Feedback</h3>
                </div>
                <div className={styles.feedbackCardBody}>
                  {results.warnings?.map((w, i) => (
                    <div key={i} className={styles.feedbackWarning}>
                      <AlertCircle size={18} className={styles.feedbackIcon} />
                      <p>{w}</p>
                    </div>
                  ))}
                  {results.recommendations?.map((r, i) => (
                    <div key={i} className={styles.feedbackRecommendation}>
                      <CheckCircle2 size={18} className={styles.feedbackIcon} />
                      <p>{r}</p>
                    </div>
                  ))}
                  {!results.warnings?.length && !results.recommendations?.length && (
                    <p className={styles.feedbackEmpty}>
                      Configuration looks solid. No specific feedback generated.
                    </p>
                  )}
                </div>
              </div>
            </>
          ) : (
            <div className={styles.emptyState}>
              Configure parameters and run analysis to see results
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
