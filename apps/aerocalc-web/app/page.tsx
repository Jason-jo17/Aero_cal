"use client";

import { useState } from "react";
import dynamic from "next/dynamic";
import Sidebar from "../components/Sidebar";
import NacaGenerator from "../components/calculators/NacaGenerator";
import PolarCurveGenerator from "../components/calculators/PolarCurveGenerator";
import WingPlanformDesigner from "../components/calculators/WingPlanformDesigner";
import MultirotorConfigurator from "../components/calculators/MultirotorConfigurator";
import MotorPropMatcher from "../components/calculators/MotorPropMatcher";
import AirfoilAnalyzer from "../components/calculators/AirfoilAnalyzer";
import { DroneConfigProvider } from "../contexts/DroneConfigContext";
import styles from "./app.module.css";

// Rapier's physics engine is WASM-backed and cannot be server-rendered;
// load it client-only so Next's SSR pass never touches it.
const DroneFlightSimulator = dynamic(
  () => import("../components/simulator/DroneFlightSimulator"),
  { ssr: false, loading: () => <div className={styles.simLoading}>Loading flight simulator…</div> }
);

export default function Home() {
  const [activeTab, setActiveTab] = useState("naca");

  return (
    <DroneConfigProvider>
      <div className={styles.appShell}>
        <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} />
        <main className={styles.mainContent}>
          <p data-testid="debug-active-tab" className={styles.srOnly}>ACTIVE_TAB_DEBUG:{activeTab}</p>
          {activeTab === "naca" && <NacaGenerator />}
          {activeTab === "polar" && <PolarCurveGenerator />}
          {activeTab === "airfoil_analysis" && <AirfoilAnalyzer />}
          {activeTab === "wing" && <WingPlanformDesigner />}
          {activeTab === "multirotor" && <MultirotorConfigurator />}
          {activeTab === "motor" && <MotorPropMatcher />}
          {activeTab === "flight_sim" && <DroneFlightSimulator />}
        </main>
      </div>
    </DroneConfigProvider>
  );
}
