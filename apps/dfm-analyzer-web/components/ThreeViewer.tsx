"use client";

import { Canvas, useLoader } from "@react-three/fiber";
import { OrbitControls, Stage, Box, Center } from "@react-three/drei";
import { Suspense } from "react";
import { STLLoader } from "three-stdlib";
import styles from "./ThreeViewer.module.css";

function STLModel({ url }: { url: string }) {
  const geometry = useLoader(STLLoader, url);
  
  return (
    <Center>
      <mesh geometry={geometry} castShadow receiveShadow>
        <meshStandardMaterial color="#8b5cf6" roughness={0.3} metalness={0.8} />
      </mesh>
    </Center>
  );
}

export default function ThreeViewer({ stlUrl }: { stlUrl?: string | null }) {
  return (
    <div className={styles.viewerRoot}>
      <Canvas shadows camera={{ position: [5, 5, 5], fov: 50 }}>
        <Suspense fallback={null}>
          <Stage environment="city" intensity={0.6}>
            {stlUrl ? (
              <STLModel url={stlUrl} />
            ) : (
              <Box args={[2, 1, 3]} castShadow receiveShadow>
                <meshStandardMaterial color="#8b5cf6" roughness={0.3} metalness={0.8} />
              </Box>
            )}
          </Stage>
        </Suspense>
        <OrbitControls makeDefault />
      </Canvas>

      <div className={styles.badge}>
        {stlUrl ? "Interactive 3D Preview (STL Uploaded)" : "Interactive 3D Preview (Placeholder geometry)"}
      </div>
    </div>
  );
}
