import sys
import os

# Add API Gateway to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "apps/api-gateway")))

from fastapi.testclient import TestClient
from api_gateway.main import app

client = TestClient(app)

def test_endpoints():
    print("Testing NACA 4-Digit Generator...")
    res = client.post("/aero/naca", json={
        "digits": "2412",
        "n_points": 100
    })
    if res.status_code == 200:
        data = res.json()
        print("[OK] NACA generated successfully. Points:", len(data.get("x_upper", [])))
    else:
        print("[FAIL] Error:", res.text)

    print("\nTesting Polar Curves...")
    res = client.post("/aero/polar-curves", json={
        "camber_percent": 2,
        "thickness_percent": 12
    })
    if res.status_code == 200:
        data = res.json()
        print("[OK] Polar curves generated. Keys:", list(data.keys()))
    else:
        print("[FAIL] Error:", res.text)
        
    print("\nTesting Wing Planform...")
    res = client.post("/aero/wing-planform", json={
        "span": 10,
        "root_chord": 2,
        "tip_chord": 1,
        "sweep_angle_deg": 15
    })
    if res.status_code == 200:
        data = res.json()
        print("[OK] Wing Planform calculated:", data.get("area"), "m2 area")
    else:
        print("[FAIL] Error:", res.text)
        
    print("\nTesting Motor Prop Matcher...")
    res = client.post("/propulsion/motor-prop-match", json={
        "motor_kv": 2300,
        "voltage": 14.8,
        "prop_diameter_in": 5.0,
        "prop_pitch_in": 4.5
    })
    if res.status_code == 200:
        data = res.json()
        print(f"[OK] Motor matched: {data.get('thrust_grams')}g thrust, {data.get('power_watts')}W power")
    else:
        print("[FAIL] Error:", res.text)


def test_aircraft_design_endpoint():
    print("\nTesting Aircraft Designer (conventional)...")
    res = client.post("/aircraft/design", json={
        "configuration_type": "conventional",
        "wing": {"span": 11.0, "root_chord": 1.6, "tip_chord": 1.6,
                  "sweep_deg": 0.0, "dihedral_deg": 5.0, "x_position": 2.0},
        "horizontal_tail": {"span": 3.4, "root_chord": 0.9, "tip_chord": 0.6,
                              "sweep_deg": 5.0, "x_position": 6.5, "z_position": 0.9},
        "vertical_tail": {"height": 1.5, "root_chord": 1.0, "tip_chord": 0.5,
                            "sweep_deg": 15.0, "x_position": 6.8, "z_position": 0.3},
        "fuselage": {"length": 8.0, "max_width": 1.2, "max_height": 1.4,
                      "nose_length": 1.5, "tail_length": 2.0},
        "mass": {"mass_kg": 1000.0, "cg_x_position": 2.56, "cruise_speed_ms": 60.0},
    })
    if res.status_code == 200:
        data = res.json()
        print("[OK] Aircraft design calculated. Static margin:",
              data["stability"]["static_margin_percent"], "% MAC")
    else:
        print("[FAIL] Error:", res.text)
    assert res.status_code == 200
    data = res.json()
    assert "geometry" in data and "stability" in data
    assert isinstance(data["stability"]["static_margin_percent"], float)


def test_aircraft_design_endpoint_rejects_mismatched_surfaces():
    print("\nTesting Aircraft Designer validation (v_tail config with horizontal_tail)...")
    res = client.post("/aircraft/design", json={
        "configuration_type": "v_tail",
        "wing": {"span": 11.0, "root_chord": 1.6, "tip_chord": 1.6, "x_position": 2.0},
        "horizontal_tail": {"span": 3.4, "root_chord": 0.9, "tip_chord": 0.6, "x_position": 6.5},
        "v_tail": {"span": 2.5, "root_chord": 0.9, "tip_chord": 0.5, "dihedral_v_deg": 40.0, "x_position": 6.7},
        "fuselage": {"length": 8.0, "max_width": 1.2, "max_height": 1.4, "nose_length": 1.5, "tail_length": 2.0},
        "mass": {"mass_kg": 1000.0, "cg_x_position": 2.56, "cruise_speed_ms": 60.0},
    })
    if res.status_code == 422:
        print("[OK] Mismatched surfaces correctly rejected with 422")
    else:
        print("[FAIL] Expected 422, got:", res.status_code, res.text)
    assert res.status_code == 422


def test_aircraft_design_endpoint_rejects_zero_span():
    print("\nTesting Aircraft Designer validation (zero-span wing)...")
    res = client.post("/aircraft/design", json={
        "configuration_type": "flying_wing",
        "wing": {"span": 0, "root_chord": 1.6, "tip_chord": 1.6, "x_position": 2.0},
        "fuselage": {"length": 8.0, "max_width": 1.2, "max_height": 1.4, "nose_length": 1.5, "tail_length": 2.0},
        "mass": {"mass_kg": 1000.0, "cg_x_position": 2.0, "cruise_speed_ms": 60.0},
    })
    if res.status_code == 422:
        print("[OK] Zero-span wing correctly rejected with 422")
    else:
        print("[FAIL] Expected 422, got:", res.status_code, res.text)
    assert res.status_code == 422

if __name__ == "__main__":
    test_endpoints()
    test_aircraft_design_endpoint()
    test_aircraft_design_endpoint_rejects_mismatched_surfaces()
    test_aircraft_design_endpoint_rejects_zero_span()
