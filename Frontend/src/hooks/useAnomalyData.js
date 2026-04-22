import { useState, useEffect, useCallback, useRef } from "react";
import { getTelemetry, predict } from "../api/endpoints";

export const useAnomalyData = (channel = "T-1", pollInterval = 5000, modelPreference = null) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const inFlightRef = useRef(false);
  const offsetRef = useRef(0);

  const fetchData = useCallback(async () => {
    if (inFlightRef.current) return;
    inFlightRef.current = true;
    setLoading(true);
    setError(null);
    try {
      const telemetry = await getTelemetry(channel, offsetRef.current, 200, 50);
      offsetRef.current = telemetry.next_offset ?? 0;

      const result = await predict(channel, telemetry.data, modelPreference);
      setData({
        ...result,
        telemetrySource: telemetry.source,
        telemetryLive: telemetry.live,
        telemetryDataset: telemetry.dataset,
        telemetryOffset: telemetry.offset,
        telemetryTotalPoints: telemetry.total_points,
      });
    } catch (err) {
      setError(err.message || "Failed to fetch anomaly data");
    } finally {
      inFlightRef.current = false;
      setLoading(false);
    }
  }, [channel, modelPreference]);

  useEffect(() => {
    offsetRef.current = 0;
  }, [channel]);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, pollInterval);
    return () => clearInterval(interval);
  }, [fetchData, pollInterval]);

  return { data, loading, error, refetch: fetchData };
};
