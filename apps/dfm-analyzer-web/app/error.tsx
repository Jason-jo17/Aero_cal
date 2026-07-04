"use client";

import { useEffect } from "react";
import styles from "./error.module.css";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className={styles.errorContainer}>
      <h2>Something went wrong in DFM Analyzer!</h2>
      <p className={styles.errorMessage}>{error.message || "An unexpected error occurred."}</p>
      <button
        onClick={() => reset()}
        className={styles.retryButton}
      >
        Try again
      </button>
    </div>
  );
}
