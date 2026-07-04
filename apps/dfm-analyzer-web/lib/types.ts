export interface DfmIssue {
  severity: "critical" | "warning";
  category: string;
  description: string;
  location?: { x: number; y: number; z: number } | null;
  recommendation?: string | null;
  cost_impact?: number | null;
}

export interface CostEstimate {
  time_breakdown?: Record<string, number>;
  cost_breakdown?: Record<string, number>;
  metrics?: Record<string, number>;
  [key: string]: unknown;
}

export interface DfmAnalysisResult {
  filename: string;
  issues: DfmIssue[];
  cost_estimate?: CostEstimate | null;
}

export function formatLocation(location: DfmIssue["location"]): string | null {
  if (!location) return null;
  const { x, y, z } = location;
  return `${x.toFixed(1)}, ${y.toFixed(1)}, ${z.toFixed(1)} mm`;
}
