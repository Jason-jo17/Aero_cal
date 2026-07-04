import { useEffect, useRef } from "react";

export interface FlightInputState {
  throttleDelta: number; // Space / Shift
  pitch: number; // W / S
  roll: number; // A / D
  yaw: number; // Q / E
  reset: boolean; // R
}

const KEY_MAP: Record<string, keyof Omit<FlightInputState, "reset">> = {
  KeyW: "pitch",
  KeyS: "pitch",
  KeyA: "roll",
  KeyD: "roll",
  KeyQ: "yaw",
  KeyE: "yaw",
  Space: "throttleDelta",
  ShiftLeft: "throttleDelta",
};

const SIGN: Record<string, number> = {
  KeyW: 1,
  KeyS: -1,
  KeyD: 1,
  KeyA: -1,
  KeyE: 1,
  KeyQ: -1,
  Space: 1,
  ShiftLeft: -1,
};

/** Tracks WASD/Space/Shift/Q/E/R key state in a ref (no re-renders) for
 * per-frame polling inside the physics loop. */
export function useKeyboardControls() {
  const state = useRef<FlightInputState>({ throttleDelta: 0, pitch: 0, roll: 0, yaw: 0, reset: false });
  const pressed = useRef<Set<string>>(new Set());

  useEffect(() => {
    const recompute = () => {
      const next: FlightInputState = { throttleDelta: 0, pitch: 0, roll: 0, yaw: 0, reset: false };
      pressed.current.forEach((code) => {
        const axis = KEY_MAP[code];
        if (axis) next[axis] += SIGN[code] ?? 0;
      });
      state.current = next;
    };

    const onKeyDown = (e: KeyboardEvent) => {
      if (e.code === "KeyR") {
        state.current = { ...state.current, reset: true };
        return;
      }
      if (KEY_MAP[e.code]) {
        pressed.current.add(e.code);
        recompute();
      }
    };
    const onKeyUp = (e: KeyboardEvent) => {
      if (e.code === "KeyR") {
        state.current = { ...state.current, reset: false };
        return;
      }
      if (KEY_MAP[e.code]) {
        pressed.current.delete(e.code);
        recompute();
      }
    };

    window.addEventListener("keydown", onKeyDown);
    window.addEventListener("keyup", onKeyUp);
    return () => {
      window.removeEventListener("keydown", onKeyDown);
      window.removeEventListener("keyup", onKeyUp);
    };
  }, []);

  return state;
}
