"use client";

import { useMemo, useRef, useState } from "react";
import * as THREE from "three";
import { Canvas, useFrame } from "@react-three/fiber";
import { OrbitControls, Html } from "@react-three/drei";
import { Physics, RigidBody, CuboidCollider, RapierRigidBody } from "@react-three/rapier";
import { useDroneConfig } from "../../contexts/DroneConfigContext";
import { useKeyboardControls } from "./useKeyboardControls";
import styles from "./DroneFlightSimulator.module.css";

const GRAVITY = 9.81;

interface MotorLayout {
  offset: [number, number, number];
  pitchSign: number;
  rollSign: number;
  yawSign: number;
}

/** Standard quad-X motor mixing: front motors give +pitch authority when
 * throttled up relative to rear, right motors give +roll, and diagonal pairs
 * spin opposite directions giving yaw authority. */
function buildQuadXLayout(armLength: number): MotorLayout[] {
  const a = armLength / Math.SQRT2;
  return [
    { offset: [-a, 0, -a], pitchSign: +1, rollSign: -1, yawSign: -1 }, // front-left
    { offset: [+a, 0, -a], pitchSign: +1, rollSign: +1, yawSign: +1 }, // front-right
    { offset: [-a, 0, +a], pitchSign: -1, rollSign: -1, yawSign: +1 }, // back-left
    { offset: [+a, 0, +a], pitchSign: -1, rollSign: +1, yawSign: -1 }, // back-right
  ];
}

function Ground() {
  return (
    <RigidBody type="fixed" colliders={false}>
      <CuboidCollider args={[50, 0.1, 50]} position={[0, -0.1, 0]} />
      <mesh receiveShadow position={[0, -0.1, 0]}>
        <boxGeometry args={[100, 0.2, 100]} />
        <meshStandardMaterial color="#3a5a40" />
      </mesh>
    </RigidBody>
  );
}

function Drone({
  massKg,
  maxThrustPerMotorN,
  hoverThrottleFraction,
  armLength,
  numMotors,
  onTelemetry,
}: {
  massKg: number;
  maxThrustPerMotorN: number;
  hoverThrottleFraction: number;
  armLength: number;
  numMotors: number;
  onTelemetry: (altitude: number, speed: number, throttlePercent: number) => void;
}) {
  const bodyRef = useRef<RapierRigidBody>(null);
  const input = useKeyboardControls();
  const throttleRef = useRef(hoverThrottleFraction);

  const layout = useMemo(() => buildQuadXLayout(armLength), [armLength]);
  const upVec = useMemo(() => new THREE.Vector3(), []);
  const quat = useMemo(() => new THREE.Quaternion(), []);
  const offsetVec = useMemo(() => new THREE.Vector3(), []);
  const worldPoint = useMemo(() => new THREE.Vector3(), []);
  const forceVec = useMemo(() => new THREE.Vector3(), []);

  useFrame((_, rawDelta) => {
    const body = bodyRef.current;
    if (!body) return;

    // Clamp delta: the first frame after WASM/physics-world init (or any tab
    // switch away and back) can report a large stalled delta, which would
    // otherwise integrate one giant, unstable step.
    const delta = Math.min(rawDelta, 1 / 30);

    const { pitch, roll, yaw, throttleDelta, reset } = input.current;

    if (reset) {
      body.setTranslation({ x: 0, y: 2, z: 0 }, true);
      body.setLinvel({ x: 0, y: 0, z: 0 }, true);
      body.setAngvel({ x: 0, y: 0, z: 0 }, true);
      body.setRotation({ x: 0, y: 0, z: 0, w: 1 }, true);
      throttleRef.current = hoverThrottleFraction;
      return;
    }

    // Base throttle tracks the calculator's real hover throttle; Space/Shift
    // move it up/down from there so the user can feel whether this
    // configuration has TWR headroom above hover or not.
    throttleRef.current = Math.min(1, Math.max(0, throttleRef.current + throttleDelta * delta * 0.5));

    const rot = body.rotation();
    quat.set(rot.x, rot.y, rot.z, rot.w);
    upVec.set(0, 1, 0).applyQuaternion(quat);

    const bodyPos = body.translation();

    if (!(window as any).__dbg) (window as any).__dbg = 0;
    const velBefore = body.linvel();
    if ((window as any).__dbg < 10) {
      console.log("DBG", (window as any).__dbg, "t", performance.now().toFixed(0), "delta", delta.toFixed(4), "velY", velBefore.y.toFixed(3));
    }
    (window as any).__dbg++;

    let totalThrustN = 0;
    for (const motor of layout) {
      const mix =
        throttleRef.current +
        pitch * 0.15 * motor.pitchSign +
        roll * 0.15 * motor.rollSign +
        yaw * 0.1 * motor.yawSign;
      const thrustN = Math.min(Math.max(mix, 0), 1) * maxThrustPerMotorN;
      totalThrustN += thrustN;

      offsetVec.set(motor.offset[0], motor.offset[1], motor.offset[2]).applyQuaternion(quat);
      worldPoint.set(bodyPos.x + offsetVec.x, bodyPos.y + offsetVec.y, bodyPos.z + offsetVec.z);
      forceVec.copy(upVec).multiplyScalar(thrustN);

      body.addForceAtPoint(
        { x: forceVec.x, y: forceVec.y, z: forceVec.z },
        { x: worldPoint.x, y: worldPoint.y, z: worldPoint.z },
        true
      );
    }
    if ((window as any).__dbg <= 10) {
      console.log("DBG totalThrustN", totalThrustN.toFixed(3), "weightN", (massKg * GRAVITY).toFixed(3));
    }

    const vel = body.linvel();
    const speed = Math.sqrt(vel.x ** 2 + vel.y ** 2 + vel.z ** 2);
    onTelemetry(bodyPos.y, speed, throttleRef.current * 100);
  });

  return (
    <RigidBody
      ref={bodyRef}
      position={[0, 2, 0]}
      colliders={false}
      linearDamping={0.4}
      angularDamping={0.9}
      canSleep={false}
    >
      {/* Explicit collider with explicit mass - the RigidBody-level `mass`
          shorthand combined with an auto `colliders="cuboid"` shape silently
          falls back to a density-derived mass (verified via instrumentation:
          it produced ~0.009kg instead of the real ~0.5kg), so mass must be
          set directly on the collider instead. */}
      <CuboidCollider args={[armLength * 0.65, 0.03, armLength * 0.65]} mass={massKg} />
      <mesh castShadow>
        <boxGeometry args={[armLength * 1.3, 0.06, armLength * 1.3]} />
        <meshStandardMaterial color="#8b5cf6" roughness={0.4} metalness={0.6} />
      </mesh>
      {buildQuadXLayout(armLength).map((m, i) => (
        <mesh key={i} position={m.offset} castShadow>
          <cylinderGeometry args={[0.06, 0.06, 0.05, 12]} />
          <meshStandardMaterial color={i < 2 ? "#22c55e" : "#ef4444"} />
        </mesh>
      ))}
    </RigidBody>
  );
}

export default function DroneFlightSimulator() {
  const { config, results } = useDroneConfig();
  const [telemetry, setTelemetry] = useState({ altitude: 2, speed: 0, throttlePercent: 0 });

  if (!results) {
    return (
      <div className={styles.emptyState}>
        Run the Multirotor Configurator first — the flight simulator is seeded by its
        calculated thrust, weight, and hover-throttle numbers.
      </div>
    );
  }

  const massKg = results.total_weight_kg;
  const maxThrustPerMotorN = (results.max_thrust_per_motor_g / 1000) * GRAVITY;
  const hoverThrottleFraction = Math.min(1, results.hover_throttle_percent / 100);
  const armLength = config.frame_size / 1000; // mm to m
  const twr = results.thrust_to_weight_ratio;

  return (
    <div className={styles.container}>
      <h2 className={styles.heading}>Drone Flight Simulator</h2>
      <p className={styles.subheading}>
        Real-time rigid-body physics driven by the Multirotor Configurator&apos;s calculated
        thrust ({maxThrustPerMotorN.toFixed(1)} N/motor), weight ({massKg.toFixed(2)} kg), and hover
        throttle ({results.hover_throttle_percent.toFixed(0)}%). TWR {twr.toFixed(2)} : 1
        {twr < 1 && " — this configuration cannot lift off; it will sink even at full throttle."}
      </p>

      <div className={styles.canvasWrap}>
        <Canvas shadows camera={{ position: [4, 3, 4], fov: 50 }}>
          <ambientLight intensity={0.5} />
          <directionalLight position={[5, 8, 5]} intensity={1.2} castShadow />
          <Physics gravity={[0, -GRAVITY, 0]}>
            <Ground />
            <Drone
              massKg={massKg}
              maxThrustPerMotorN={maxThrustPerMotorN}
              hoverThrottleFraction={hoverThrottleFraction}
              armLength={armLength}
              numMotors={config.num_motors}
              onTelemetry={(altitude, speed, throttlePercent) => setTelemetry({ altitude, speed, throttlePercent })}
            />
          </Physics>
          <OrbitControls makeDefault target={[0, 1, 0]} />
          <Html position={[0, 0, 0]} calculatePosition={() => [16, 16, 0]} style={{ pointerEvents: "none" }}>
            <div className={styles.hud}>
              <div>Altitude: {telemetry.altitude.toFixed(2)} m</div>
              <div>Speed: {telemetry.speed.toFixed(2)} m/s</div>
              <div>Throttle: {telemetry.throttlePercent.toFixed(0)}%</div>
            </div>
          </Html>
        </Canvas>
      </div>

      <p className={styles.controls}>
        <strong>Controls:</strong> W/S pitch · A/D roll · Q/E yaw · Space/Shift throttle up/down · R reset
      </p>
    </div>
  );
}
