import { useState, useEffect, useCallback } from "react";
import { predict } from "../api/endpoints";

const NUM_FEATURES = 25; // SMAP dataset has 25 telemetry features per timestep

const generateDummyData = (length = 200) =>
  Array.from({ length }, () =>
    Array.from({ length: NUM_FEATURES }, () =>
      parseFloat((Math.random() * 2 - 1).toFixed(4))
    )
  );

export const useAnomalyData = (channel = "T-1", pollInterval = 5000, modelPreference = null) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const inputData = generateDummyData(200);
      const result = await predict(channel, inputData, modelPreference);
      setData(result);
    } catch (err) {
      setError(err.message || "Failed to fetch anomaly data");
    } finally {
      setLoading(false);
    }
  }, [channel, modelPreference]);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, pollInterval);
    return () => clearInterval(interval);
  }, [fetchData, pollInterval]);

  return { data, loading, error, refetch: fetchData };
};