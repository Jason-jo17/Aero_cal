"use client";

import { createContext, useContext, useState, ReactNode } from "react";
import { DroneConfig, PerformanceResults } from "../lib/types";

export const DEFAULT_DRONE_CONFIG: DroneConfig = {
  frame_type: "quadcopter",
  frame_size: 250,
  motor_kv: 2300,
  motor_max_current: 30,
  motor_weight: 30,
  motor_efficiency: 0.85,
  num_motors: 4,
  prop_diameter: 5,
  prop_pitch: 4,
  prop_blades: 3,
  battery_cells: 4,
  battery_capacity: 1500,
  battery_c_rating: 75,
  battery_weight: 170,
  esc_weight: 10,
  fc_weight: 15,
  frame_weight: 100,
  payload_weight: 0,
};

interface DroneConfigContextValue {
  config: DroneConfig;
  setConfig: (config: DroneConfig) => void;
  results: PerformanceResults | null;
  setResults: (results: PerformanceResults | null) => void;
}

const DroneConfigContext = createContext<DroneConfigContextValue | null>(null);

export function DroneConfigProvider({ children }: { children: ReactNode }) {
  const [config, setConfig] = useState<DroneConfig>(DEFAULT_DRONE_CONFIG);
  const [results, setResults] = useState<PerformanceResults | null>(null);

  return (
    <DroneConfigContext.Provider value={{ config, setConfig, results, setResults }}>
      {children}
    </DroneConfigContext.Provider>
  );
}

export function useDroneConfig(): DroneConfigContextValue {
  const ctx = useContext(DroneConfigContext);
  if (!ctx) {
    throw new Error("useDroneConfig must be used within a DroneConfigProvider");
  }
  return ctx;
}
