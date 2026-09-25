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
        print("OK NACA generated successfully. Points:", len(data.get("x_upper", [])))
    else:
        print("FAIL Error:", res.text)

    print("\nTesting Polar Curves...")
    res = client.post("/aero/polar-curves", json={
        "camber_percent": 2,
        "thickness_percent": 12
    })
    if res.status_code == 200:
        data = res.json()
        print("OK Polar curves generated. Keys:", list(data.keys()))
    else:
        print("FAIL Error:", res.text)
        
    print("\nTesting Wing Planform...")
    res = client.post("/aero/wing-planform", json={
        "span": 10,
        "root_chord": 2,
        "tip_chord": 1,
        "sweep_angle_deg": 15
    })
    if res.status_code == 200:
        data = res.json()
        print("OK Wing Planform calculated:", data)
    else:
        print("FAIL Error:", res.text)
        
    print("\nTesting Motor Prop Matcher...")
    res = client.post("/propulsion/motor-prop-match", json={
        "motor_kv": 2300,
        "voltage": 14.8,
        "prop_diameter_in": 5.0,
        "prop_pitch_in": 4.5
    })
    if res.status_code == 200:
        data = res.json()
        print("OK Motor matched:", data)
    else:
        print("FAIL Error:", res.text)

if __name__ == "__main__":
    test_endpoints()
