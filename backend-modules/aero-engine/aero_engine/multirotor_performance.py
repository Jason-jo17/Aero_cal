import numpy as np
from dataclasses import dataclass
from typing import Dict, List, Tuple

@dataclass
class MultirotorConfig:
    frame_type: str
    frame_size: float
    motor_kv: float
    motor_max_current: float
    motor_weight: float
    prop_diameter: float
    prop_pitch: float
    motor_efficiency: float = 0.85
    num_motors: int = 4
    prop_blades: int = 2
    battery_cells: int = 3
    battery_capacity: float = 2200
    battery_c_rating: float = 20
    battery_weight: float = 200
    esc_weight: float = 30
    fc_weight: float = 20
    frame_weight: float = 300
    payload_weight: float = 0
    required_flight_time: float = 0

@dataclass
class PerformanceResults:
    total_weight_g: float
    total_weight_kg: float
    weight_breakdown: Dict[str, float]
    max_thrust_total_g: float
    max_thrust_per_motor_g: float
    thrust_to_weight_ratio: float
    hover_throttle_percent: float
    hover_power_w: float
    max_power_w: float
    hover_current_a: float
    max_current_a: float
    max_flight_time_min: float
    cruise_flight_time_min: float
    estimated_range_km: float
    max_speed_ms: float
    max_climb_rate_ms: float
    specific_thrust_gW: float
    power_loading_gW: float
    warnings: List[str]
    recommendations: List[str]

class MultirotorCalculator:
    CT_BASE = 0.1
    CP_BASE = 0.05
    
    def __init__(self):
        self.gravity = 9.81
        self.air_density = 1.225
    
    def calculate_performance(self, config: MultirotorConfig) -> PerformanceResults:
        weight_breakdown = self._calculate_weight_breakdown(config)
        total_weight_g = sum(weight_breakdown.values())
        total_weight_kg = total_weight_g / 1000.0
        total_weight_n = total_weight_kg * self.gravity
        
        voltage = self._cell_voltage(config.battery_cells)
        max_rpm = config.motor_kv * voltage
        rpm_range = np.linspace(0, max_rpm, 100)
        
        thrust_per_motor, power_per_motor = self._calculate_thrust_power_curves(config, rpm_range)
        hover_idx, hover_throttle = self._find_hover_point(thrust_per_motor, config.num_motors, total_weight_g)
        
        hover_power_per_motor = power_per_motor[hover_idx]
        hover_power_total = hover_power_per_motor * config.num_motors
        hover_current = hover_power_total / voltage
        
        max_thrust_per_motor = thrust_per_motor[-1]
        max_thrust_total = max_thrust_per_motor * config.num_motors
        max_power_per_motor = power_per_motor[-1]
        max_power_total = max_power_per_motor * config.num_motors
        max_current = max_power_total / voltage
        
        twr = max_thrust_total / total_weight_g if total_weight_g > 0 else 0
        
        battery_capacity_ah = config.battery_capacity / 1000.0
        usable_capacity = battery_capacity_ah * 0.8
        
        if hover_current > 0:
            max_flight_time = (usable_capacity / hover_current) * 60
        else:
            max_flight_time = 0
            
        cruise_idx = self._find_cruise_point(thrust_per_motor, power_per_motor, config.num_motors, total_weight_g)
        cruise_power = power_per_motor[cruise_idx] * config.num_motors
        cruise_current = cruise_power / voltage
        
        if cruise_current > 0:
            cruise_flight_time = (usable_capacity / cruise_current) * 60
        else:
            cruise_flight_time = max_flight_time
            
        max_speed = self._estimate_max_speed(max_thrust_total, total_weight_g, config)
        max_climb_rate = self._estimate_climb_rate(max_thrust_total, total_weight_g)
        
        cruise_speed = max_speed * 0.7
        estimated_range = (cruise_flight_time / 60) * (cruise_speed * 3.6)
        
        specific_thrust = max_thrust_total / max_power_total if max_power_total > 0 else 0
        power_loading = total_weight_g / hover_power_total if hover_power_total > 0 else 0
        
        warnings, recommendations = self._generate_feedback(config, twr, hover_throttle, max_current, max_flight_time)
        
        return PerformanceResults(
            total_weight_g=total_weight_g, total_weight_kg=total_weight_kg,
            weight_breakdown=weight_breakdown, max_thrust_total_g=max_thrust_total,
            max_thrust_per_motor_g=max_thrust_per_motor, thrust_to_weight_ratio=twr,
            hover_throttle_percent=hover_throttle, hover_power_w=hover_power_total,
            max_power_w=max_power_total, hover_current_a=hover_current, max_current_a=max_current,
            max_flight_time_min=max_flight_time, cruise_flight_time_min=cruise_flight_time,
            estimated_range_km=estimated_range, max_speed_ms=max_speed,
            max_climb_rate_ms=max_climb_rate, specific_thrust_gW=specific_thrust,
            power_loading_gW=power_loading, warnings=warnings, recommendations=recommendations
        )

    def _calculate_weight_breakdown(self, config: MultirotorConfig) -> Dict[str, float]:
        breakdown = {
            'motors': config.motor_weight * config.num_motors,
            'propellers': 10 * config.num_motors,
            'escs': config.esc_weight * config.num_motors,
            'battery': config.battery_weight,
            'flight_controller': config.fc_weight,
            'frame': config.frame_weight,
            'payload': config.payload_weight,
        }
        component_weight = sum(breakdown.values())
        breakdown['wiring_misc'] = component_weight * 0.05
        return breakdown

    def _cell_voltage(self, cells: int, state: str = 'nominal') -> float:
        voltages = {'nominal': 3.7, 'charged': 4.2, 'depleted': 3.0, 'storage': 3.8}
        return cells * voltages.get(state, 3.7)

    def _calculate_thrust_power_curves(self, config: MultirotorConfig, rpm_range: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        D_m = config.prop_diameter * 0.0254
        n_rps = rpm_range / 60.0
        pitch_ratio = config.prop_pitch / config.prop_diameter
        CT = self.CT_BASE * (1 + 0.2 * pitch_ratio)
        CP = self.CP_BASE * (1 + 0.3 * pitch_ratio)
        thrust_n = CT * self.air_density * (n_rps**2) * (D_m**4)
        thrust_g = thrust_n * 1000 / self.gravity
        power_w = CP * self.air_density * (n_rps**3) * (D_m**5)
        power_electrical = power_w / config.motor_efficiency
        return thrust_g, power_electrical

    def _find_hover_point(self, thrust_per_motor: np.ndarray, num_motors: int, total_weight_g: float) -> Tuple[int, float]:
        total_thrust = thrust_per_motor * num_motors
        hover_idx = np.argmin(np.abs(total_thrust - total_weight_g))
        hover_throttle = (hover_idx / len(thrust_per_motor)) * 100
        return hover_idx, hover_throttle

    def _find_cruise_point(self, thrust_per_motor: np.ndarray, power_per_motor: np.ndarray, num_motors: int, total_weight_g: float) -> int:
        total_thrust = thrust_per_motor * num_motors
        total_power = power_per_motor * num_motors
        with np.errstate(divide='ignore', invalid='ignore'):
            efficiency = total_thrust / total_power
            efficiency = np.nan_to_num(efficiency)
        valid_points = total_thrust > total_weight_g
        efficiency[~valid_points] = 0
        return np.argmax(efficiency)

    def _estimate_max_speed(self, max_thrust_g: float, weight_g: float, config: MultirotorConfig) -> float:
        tilt_angle_rad = np.radians(45)
        horizontal_thrust_g = max_thrust_g * np.sin(tilt_angle_rad)
        prop_diameter_m = config.prop_diameter * 0.0254
        area_m2 = np.pi * (prop_diameter_m / 2)**2
        horizontal_thrust_n = horizontal_thrust_g * self.gravity / 1000
        cd = 1.0
        v_max = np.sqrt(2 * horizontal_thrust_n / (self.air_density * area_m2 * cd)) if horizontal_thrust_n > 0 else 0
        return v_max

    def _estimate_climb_rate(self, max_thrust_g: float, weight_g: float) -> float:
        excess_thrust_g = max_thrust_g - weight_g
        excess_thrust_n = excess_thrust_g * self.gravity / 1000
        weight_kg = weight_g / 1000 if weight_g > 0 else 1
        available_thrust = excess_thrust_n * 0.5
        climb_rate = available_thrust * self.gravity / weight_kg
        return max(min(climb_rate, 15.0), 0.0)

    def _generate_feedback(self, config: MultirotorConfig, twr: float, hover_throttle: float, max_current: float, flight_time: float) -> Tuple[List[str], List[str]]:
        warnings, recommendations = [], []
        if twr < 2.0:
            warnings.append(f"Low TWR ({twr:.2f}). Drone will be sluggish.")
        elif twr > 5.0:
            recommendations.append(f"Excellent TWR ({twr:.2f}) for acrobatic flight")
        if hover_throttle > 65:
            warnings.append(f"High hover throttle ({hover_throttle:.1f}%). Limited headroom.")
        elif hover_throttle < 30:
            recommendations.append(f"Low hover throttle ({hover_throttle:.1f}%) provides good efficiency")
        battery_capacity_ah = config.battery_capacity / 1000.0
        max_continuous_current = battery_capacity_ah * config.battery_c_rating
        if max_current > max_continuous_current:
            warnings.append(f"Peak current ({max_current:.1f}A) exceeds battery rating.")
        if flight_time < 10:
            warnings.append(f"Short flight time ({flight_time:.1f} min)")
        return warnings, recommendations
