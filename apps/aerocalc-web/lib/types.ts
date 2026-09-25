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

/** Mirrors aero_engine.aircraft.models.Surface */
export interface AircraftSurface {
  span: number;
  root_chord: number;
  tip_chord: number;
  sweep_deg?: number;
  dihedral_deg?: number;
  twist_deg?: number;
  airfoil?: string;
  x_position: number;
  z_position?: number;
  mount?: "high" | "mid" | "low";
}

/** Mirrors aero_engine.aircraft.models.VerticalTail */
export interface AircraftVerticalTail {
  height: number;
  root_chord: number;
  tip_chord: number;
  sweep_deg?: number;
  airfoil?: string;
  x_position: number;
  z_position?: number;
}

/** Mirrors aero_engine.aircraft.models.VTail */
export interface AircraftVTail {
  span: number;
  root_chord: number;
  tip_chord: number;
  dihedral_v_deg: number;
  sweep_deg?: number;
  airfoil?: string;
  x_position: number;
  z_position?: number;
}

/** Mirrors aero_engine.aircraft.models.Fuselage */
export interface AircraftFuselage {
  length: number;
  max_width: number;
  max_height: number;
  nose_length: number;
  tail_length: number;
}

/** Mirrors aero_engine.aircraft.models.MassProperties */
export interface AircraftMassProperties {
  mass_kg: number;
  cg_x_position: number;
  cruise_speed_ms: number;
}

export type AircraftConfigurationType =
  | "conventional"
  | "flying_wing"
  | "canard"
  | "t_tail"
  | "v_tail";

/** Mirrors aero_engine.aircraft.models.AircraftConfig */
export interface AircraftConfig {
  configuration_type: AircraftConfigurationType;
  wing: AircraftSurface;
  horizontal_tail?: AircraftSurface | null;
  vertical_tail?: AircraftVerticalTail | null;
  canard?: AircraftSurface | null;
  v_tail?: AircraftVTail | null;
  fuselage: AircraftFuselage;
  mass: AircraftMassProperties;
}

/** Mirrors one surface's entry in aero_engine.aircraft.geometry.generate_aircraft_geometry output */
export interface SurfaceGeometry {
  top_view: number[][];
  front_view: number[][];
  side_view: number[][];
  vertices: number[][];
  edges: number[][];
  planform: {
    span: number;
    root_chord: number;
    tip_chord: number;
    sweep_angle_deg: number;
    taper_ratio: number;
    area: number;
    aspect_ratio: number;
    mac: number;
    y_mac: number;
    x_mac_le: number;
  } | null;
}

/** Mirrors aero_engine.aircraft.geometry.generate_aircraft_geometry output */
export interface AircraftGeometry {
  wing: SurfaceGeometry;
  horizontal_tail: SurfaceGeometry | null;
  vertical_tail: SurfaceGeometry | null;
  canard: SurfaceGeometry | null;
  v_tail: SurfaceGeometry | null;
  fuselage: SurfaceGeometry;
}

/** Mirrors aero_engine.aircraft.stability.analyze_stability output */
export interface StabilityResult {
  neutral_point_mac: number;
  cg_mac: number;
  static_margin_percent: number;
  static_margin_classification: "unstable" | "marginal" | "stable" | "stable_sluggish";
  cm_alpha: number;
  tail_volume_coefficient: number | null;
  cl_beta: number;
  cl_beta_classification: "unstable" | "marginal" | "stable";
  cn_beta: number;
  cn_beta_classification: "unstable" | "marginal" | "stable";
  vertical_tail_volume_coefficient: number | null;
  warnings: string[];
}

/** Mirrors the response body of POST /aircraft/design */
export interface AircraftDesignResponse {
  geometry: AircraftGeometry;
  stability: StabilityResult;
}
