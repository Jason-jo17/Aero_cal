import { AlertTriangle, XCircle, CheckCircle, Info, ArrowRight, DollarSign } from "lucide-react";
import styles from "./AnalysisResults.module.css";
import { DfmAnalysisResult, formatLocation } from "../lib/types";

export default function AnalysisResults({ results }: { results: DfmAnalysisResult | null }) {
  if (!results) {
    return (
      <div className={styles.emptyState}>
        Upload a part and run analysis to see results
      </div>
    );
  }

  const issues = results.issues || [];

  const criticalCount = issues.filter((i) => i.severity === "critical").length;
  const warningCount = issues.filter((i) => i.severity === "warning").length;
  const cost = results.cost_estimate;

  return (
    <div>
      {/* Summary */}
      <div className={styles.summaryCard}>
        <div>
          <h3 className={styles.summaryTitle}>Analysis Summary</h3>
          <p className={styles.summaryMeta}>
            Part: {results.filename}
          </p>
        </div>
        <div className={styles.summaryCounters}>
          <div className={styles.counter}>
            <div className={`${styles.counterValue} ${styles.counterValueCritical}`}>
              {criticalCount}
            </div>
            <div className={styles.counterLabel}>Critical</div>
          </div>
          <div className={styles.counter}>
            <div className={`${styles.counterValue} ${styles.counterValueWarning}`}>
              {warningCount}
            </div>
            <div className={styles.counterLabel}>Warnings</div>
          </div>
        </div>
      </div>

      {/* Cost estimate */}
      {cost?.cost_breakdown && (
        <div className={`${styles.issuesCard} ${styles.costCard}`}>
          <div className={styles.issuesCardHeader}>
            <h4 className={styles.issuesCardTitle}>
              <DollarSign size={16} style={{ display: "inline", verticalAlign: "middle", marginRight: 4 }} />
              Cost Estimate
            </h4>
          </div>
          <div className={styles.issuesCardBody}>
            {Object.entries(cost.cost_breakdown).map(([key, value]) => (
              <div key={key} className={styles.issueBadgeRow}>
                <span className={styles.issueRuleName}>{key.replace(/_/g, " ")}</span>
                <span>{typeof value === "number" ? value.toFixed(2) : String(value)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Issues list */}
      <div className={styles.issuesCard}>
        <div className={styles.issuesCardHeader}>
          <h4 className={styles.issuesCardTitle}>Detected Issues</h4>
        </div>
        <div className={styles.issuesCardBody}>
          {issues.length === 0 ? (
            <div className={styles.noIssues}>
              <CheckCircle size={20} />
              <span>No manufacturability issues detected. Part is ready for production.</span>
            </div>
          ) : (
            issues.map((issue, index) => {
              const locationStr = formatLocation(issue.location);
              return (
                <div
                  key={index}
                  className={`${styles.issueItem} ${
                    issue.severity === "critical"
                      ? styles.issueItemCritical
                      : styles.issueItemWarning
                  }`}
                >
                  <div className={styles.issueIcon}>
                    {issue.severity === "critical" ? (
                      <XCircle size={20} color="#dc2626" />
                    ) : (
                      <AlertTriangle size={20} color="#ea580c" />
                    )}
                  </div>
                  <div className={styles.issueContent}>
                    <div className={styles.issueBadgeRow}>
                      <span
                        className={`${styles.issueSeverityBadge} ${
                          issue.severity === "critical"
                            ? styles.issueSeverityCritical
                            : styles.issueSeverityWarning
                        }`}
                      >
                        {issue.severity}
                      </span>
                      <span className={styles.issueRuleName}>
                        • {issue.category.replace(/_/g, " ")}
                      </span>
                      {typeof issue.cost_impact === "number" && issue.cost_impact > 0 && (
                        <span className={styles.issueRuleName}>
                          (+{(issue.cost_impact * 100).toFixed(0)}% cost)
                        </span>
                      )}
                    </div>
                    <p className={styles.issueDescription}>{issue.description}</p>
                    {issue.recommendation && (
                      <p className={`${styles.issueDescription} ${styles.recommendationText}`}>
                        <ArrowRight size={14} style={{ display: "inline", verticalAlign: "middle", marginRight: 4 }} />
                        {issue.recommendation}
                      </p>
                    )}
                    {locationStr && (
                      <div className={styles.issueLocation}>
                        <Info size={14} />
                        Location: {locationStr}
                      </div>
                    )}
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}
