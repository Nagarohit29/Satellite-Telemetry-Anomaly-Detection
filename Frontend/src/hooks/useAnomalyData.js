import { useState, useEffect, useCallback } from "react";
import { predict } from "../api/endpoints";

const generateDummyData = (length = 200) =>
  Array.from({ length }, () => parseFloat((Math.random() * 2 - 1).toFixed(4)));

export const useAnomalyData = (channel = "T-1", pollInterval = 5000) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const inputData = generateDummyData(200);
      const result = await predict(channel, inputData);
      setData(result);
    } catch (err) {
      setError(err.message || "Failed to fetch anomaly data");
    } finally {
      setLoading(false);
    }
  }, [channel]);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, pollInterval);
    return () => clearInterval(interval);
  }, [fetchData, pollInterval]);

  return { data, loading, error, refetch: fetchData };
};