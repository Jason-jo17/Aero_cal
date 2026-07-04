"use client";

import { useState, useRef, useEffect } from "react";
import ThreeViewer from "../components/ThreeViewer";
import AnalysisResults from "../components/AnalysisResults";
import AiAssistant from "../components/AiAssistant";
import { UploadCloud } from "lucide-react";
import styles from "./page.module.css";
import { DfmAnalysisResult } from "../lib/types";

type Engine = "cnc" | "fdm" | "injection" | "sheet";

const MATERIALS_BY_ENGINE: Record<Engine, string[]> = {
  cnc: ["aluminum_6061", "aluminum_7075", "steel_1018", "stainless_304", "titanium_grade5", "brass", "copper"],
  fdm: ["pla", "abs", "pc", "pp", "nylon", "pet"],
  injection: ["abs", "pc", "pp", "nylon", "pet"],
  sheet: ["steel", "aluminum_6061", "stainless_304"],
};

export default function Home() {
  const [results, setResults] = useState<DfmAnalysisResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [activeEngine, setActiveEngine] = useState<Engine>("cnc");
  const [material, setMaterial] = useState(MATERIALS_BY_ENGINE.cnc[0] ?? "aluminum_6061");

  const [file, setFile] = useState<File | null>(null);
  const [fileUrl, setFileUrl] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleEngineChange = (engine: Engine) => {
    setActiveEngine(engine);
    setMaterial(MATERIALS_BY_ENGINE[engine][0] ?? "aluminum_6061");
  };

  // Cleanup blob URL when component unmounts or fileUrl changes
  useEffect(() => {
    return () => {
      if (fileUrl) {
        URL.revokeObjectURL(fileUrl);
      }
    };
  }, [fileUrl]);

  const handleFile = (newFile: File) => {
    if (!newFile.name.toLowerCase().endsWith(".stl")) {
      alert("Please upload an STL file.");
      return;
    }
    setFile(newFile);
    if (fileUrl) {
      URL.revokeObjectURL(fileUrl);
    }
    const url = URL.createObjectURL(newFile);
    setFileUrl(url);
    setResults(null);
  };

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const droppedFile = e.dataTransfer.files.item(0);
      if (droppedFile) {
        handleFile(droppedFile);
      }
    }
  };

  const onDragOver = (e: React.DragEvent) => {
    e.preventDefault();
  };

  const onFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const selectedFile = e.target.files.item(0);
      if (selectedFile) {
        handleFile(selectedFile);
      }
    }
  };

  const handleRunAnalysis = async () => {
    if (!file) {
      alert("Please upload an STL file first.");
      return;
    }

    setLoading(true);
    try {
      const baseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const url =
        activeEngine === "cnc"
          ? `${baseUrl}/dfm/analyze-cnc`
          : activeEngine === "fdm"
          ? `${baseUrl}/dfm/analyze-fdm`
          : activeEngine === "injection"
          ? `${baseUrl}/dfm/analyze-injection`
          : `${baseUrl}/dfm/analyze-sheet-metal`;

      const formData = new FormData();
      formData.append("file", file);
      formData.append("material", material);
      formData.append("include_cost", "true");

      const res = await fetch(url, {
        method: "POST",
        body: formData,
      });
      
      const data = await res.json();
      setResults(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={styles.pageShell}>
      <header className={styles.header}>
        <div className={styles.headerBrand}>
          <h1>DFM-Analyzer</h1>
          <p>Manufacturing Rules Engine</p>
        </div>
        <div className={styles.engineToggleGroup}>
          <button
            type="button"
            onClick={() => handleEngineChange("cnc")}
            className={`${styles.engineBtn} ${activeEngine === "cnc" ? styles.engineBtnActive : ""}`}
            title="Select CNC Milling analysis engine"
          >
            CNC Milling
          </button>
          <button
            type="button"
            onClick={() => handleEngineChange("fdm")}
            className={`${styles.engineBtn} ${activeEngine === "fdm" ? styles.engineBtnActive : ""}`}
            title="Select FDM 3D Printing analysis engine"
          >
            FDM 3D Printing
          </button>
          <button
            type="button"
            onClick={() => handleEngineChange("injection")}
            className={`${styles.engineBtn} ${activeEngine === "injection" ? styles.engineBtnActive : ""}`}
            title="Select Injection Molding analysis engine"
          >
            Injection Molding
          </button>
          <button
            type="button"
            onClick={() => handleEngineChange("sheet")}
            className={`${styles.engineBtn} ${activeEngine === "sheet" ? styles.engineBtnActive : ""}`}
            title="Select Sheet Metal analysis engine"
          >
            Sheet Metal
          </button>
        </div>
      </header>

      <main className={styles.main}>
        <div className={styles.twoCol}>
          {/* Left column: Upload & 3D View */}
          <div className={styles.leftCol}>
            <div 
              className={styles.uploadZone} 
              onDrop={onDrop} 
              onDragOver={onDragOver}
              onClick={() => fileInputRef.current?.click()}
            >
              <input 
                type="file" 
                accept=".stl"
                ref={fileInputRef} 
                onChange={onFileChange} 
                className={styles.fileInput}
                title="Upload STL file"
                placeholder="Upload STL"
                aria-label="Upload CAD File"
              />
              <UploadCloud size={32} color="#888" className={styles.uploadIcon} />
              <h3 className={styles.uploadTitle}>
                {file ? file.name : "Upload CAD Model"}
              </h3>
              <p className={styles.uploadSubtitle}>
                {file ? "Click or drag to replace" : "Drag & drop an STL file here"}
              </p>
            </div>

            <div className={styles.viewerWrap}>
              <ThreeViewer stlUrl={fileUrl} />
            </div>

            <label htmlFor="material-select" className={styles.uploadSubtitle}>
              Material
            </label>
            <select
              id="material-select"
              value={material}
              onChange={(e) => setMaterial(e.target.value)}
              className={styles.engineBtn}
              title="Material for cost estimation"
            >
              {MATERIALS_BY_ENGINE[activeEngine].map((m) => (
                <option key={m} value={m}>
                  {m.replace(/_/g, " ")}
                </option>
              ))}
            </select>

            <button
              type="button"
              onClick={handleRunAnalysis}
              disabled={loading || !file}
              className={styles.runBtn}
              title={`Run ${activeEngine.toUpperCase()} manufacturability analysis`}
            >
              {loading
                ? "Running DFM Analysis…"
                : `Run ${activeEngine.toUpperCase()} Analysis`}
            </button>
          </div>

          {/* Right column: Results */}
          <div className={styles.rightCol}>
            <AnalysisResults results={results} />
            {results && results.issues && (
              <AiAssistant 
                partName={file?.name} 
                manufacturingProcess={activeEngine}
                issues={results.issues}
              />
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
