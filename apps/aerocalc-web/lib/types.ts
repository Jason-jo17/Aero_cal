export interface DroneConfig {
  frame_type: string;
  frame_size: number;
  motor_kv: number;
  motor_max_current: number;
  motor_weight: number;
  motor_efficiency: number;
  num_motors: number;
  prop_diameter: number;
  prop_pitch: number;
  prop_blades: number;
  battery_cells: number;
  battery_capacity: number;
  battery_c_rating: number;
  battery_weight: number;
  esc_weight: number;
  fc_weight: number;
  frame_weight: number;
  payload_weight: number;
}

/** Mirrors aero_engine.multirotor_performance.PerformanceResults */
export interface PerformanceResults {
  total_weight_g: number;
  total_weight_kg: number;
  max_thrust_total_g: number;
  max_thrust_per_motor_g: number;
  thrust_to_weight_ratio: number;
  hover_throttle_percent: number;
  hover_power_w: number;
  max_power_w: number;
  max_flight_time_min: number;
  cruise_flight_time_min: number;
  max_speed_ms: number;
  max_climb_rate_ms: number;
  warnings?: string[];
  recommendations?: string[];
}
