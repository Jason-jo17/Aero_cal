import { Plane, Cpu, Activity, LayoutTemplate, Fan, FileBarChart, Rocket } from "lucide-react";
import styles from "./Sidebar.module.css";

interface SidebarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
}

export default function Sidebar({ activeTab, setActiveTab }: SidebarProps) {
  return (
    <div className={styles.sidebar}>
      <div className={styles.brand}>
        <h1 className={styles.brandTitle}>AeroCalc-Suite</h1>
        <p className={styles.brandSubtitle}>Engineering Tools</p>
      </div>

      <nav>
        <ul className={styles.nav}>
          <li className={styles.navItem}>
            <button
              type="button"
              onClick={() => setActiveTab("naca")}
              className={`${styles.navButton} ${activeTab === "naca" ? styles.navButtonActive : ""}`}
              title="NACA Airfoil Generator"
            >
              <Plane size={18} />
              NACA Generator
            </button>
          </li>
          <li className={styles.navItem}>
            <button
              type="button"
              onClick={() => setActiveTab("polar")}
              className={`${styles.navButton} ${activeTab === "polar" ? styles.navButtonActive : ""}`}
              title="Polar Curve Generator"
            >
              <Activity size={18} />
              Polar Curves
            </button>
          </li>
          <li className={styles.navItem}>
            <button
              type="button"
              onClick={() => setActiveTab("airfoil_analysis")}
              className={`${styles.navButton} ${activeTab === "airfoil_analysis" ? styles.navButtonActive : ""}`}
              title="Airfoil Analysis (Panel Method)"
            >
              <FileBarChart size={18} />
              Airfoil Analysis
            </button>
          </li>
          <li className={styles.navItem}>
            <button
              type="button"
              onClick={() => setActiveTab("wing")}
              className={`${styles.navButton} ${activeTab === "wing" ? styles.navButtonActive : ""}`}
              title="Wing Planform Designer"
            >
              <LayoutTemplate size={18} />
              Wing Planform
            </button>
          </li>
          <li className={styles.navItem}>
            <button
              type="button"
              onClick={() => setActiveTab("multirotor")}
              className={`${styles.navButton} ${activeTab === "multirotor" ? styles.navButtonActive : ""}`}
              title="Multirotor Configurator"
            >
              <Cpu size={18} />
              Multirotor Config
            </button>
          </li>
          <li className={styles.navItem}>
            <button
              type="button"
              onClick={() => setActiveTab("motor")}
              className={`${styles.navButton} ${activeTab === "motor" ? styles.navButtonActive : ""}`}
              title="Motor-Prop Matcher"
            >
              <Fan size={18} />
              Motor-Prop Matcher
            </button>
          </li>
          <li className={styles.navItem}>
            <button
              type="button"
              onClick={() => setActiveTab("flight_sim")}
              className={`${styles.navButton} ${activeTab === "flight_sim" ? styles.navButtonActive : ""}`}
              title="Drone Flight Simulator"
            >
              <Rocket size={18} />
              Flight Simulator
            </button>
          </li>
        </ul>
      </nav>
    </div>
  );
}
