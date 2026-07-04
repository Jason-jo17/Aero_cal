"use client";

import { useState } from "react";
import { Loader2, Bot, Sparkles, AlertCircle } from "lucide-react";
import styles from "./AiAssistant.module.css";
import { DfmIssue } from "../lib/types";

interface AiAssistantProps {
  partName?: string;
  manufacturingProcess?: string;
  issues: DfmIssue[];
}

export default function AiAssistant({ partName = "Upload.stl", manufacturingProcess = "cnc", issues }: AiAssistantProps) {
  const [summary, setSummary] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const getDesignReview = async () => {
    setLoading(true);
    setError(null);
    try {
      const baseUrl = process.env.NEXT_PUBLIC_AI_AGENT_URL || "http://localhost:8001";
      const res = await fetch(`${baseUrl}/ai/design-review`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          part_name: partName,
          manufacturing_process: manufacturingProcess,
          issues: issues
        })
      });

      if (!res.ok) {
        throw new Error("Failed to get AI review");
      }

      const data = await res.json();
      setSummary(data.summary);
    } catch (err) {
      setError(err instanceof Error ? err.message : "An error occurred");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <div className={styles.headerIcon}>
          <Bot size={20} color="#6366f1" />
        </div>
        <h3 className={styles.title}>AI Design Assistant</h3>
      </div>
      
      {!summary && !loading && (
        <div className={styles.promptArea}>
          <p className={styles.description}>
            Get an instant, AI-generated design review based on the manufacturability issues detected above.
          </p>
          <button
            type="button"
            onClick={getDesignReview}
            className={styles.button}
            disabled={issues.length === 0}
            title={issues.length === 0 ? "No issues to review yet" : "Generate AI review"}
          >
            <Sparkles size={16} />
            Generate Review
          </button>
        </div>
      )}

      {loading && (
        <div className={styles.loadingArea}>
          <Loader2 className={styles.spinner} size={24} />
          <p>Analyzing geometry and generating insights...</p>
        </div>
      )}

      {error && (
        <div className={styles.error}>
          <AlertCircle size={16} />
          <span>{error}</span>
        </div>
      )}

      {summary && !loading && (
        <div className={styles.chatArea}>
          <div className={styles.message}>
            <div className={styles.avatar}>
              <Bot size={16} color="white" />
            </div>
            <div className={styles.bubble}>
              {summary.split("\n\n").map((para, i) => (
                <p key={i}>{para}</p>
              ))}
            </div>
          </div>
          <button type="button" onClick={() => setSummary(null)} className={styles.resetBtn}>
            Reset Chat
          </button>
        </div>
      )}
    </div>
  );
}
