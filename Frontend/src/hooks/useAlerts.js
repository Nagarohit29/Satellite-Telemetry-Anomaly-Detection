import { useState, useEffect, useCallback } from "react";
import { getAlerts, clearAlerts } from "../api/endpoints";

export const useAlerts = (pollInterval = 8000) => {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchAlerts = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getAlerts();
      setAlerts(data);
      setError(null);
    } catch (err) {
      setError(err.message || "Failed to fetch alerts");
    } finally {
      setLoading(false);
    }
  }, []);

  const deleteAlerts = async () => {
    await clearAlerts();
    setAlerts([]);
  };

  useEffect(() => {
    fetchAlerts();
    const interval = setInterval(fetchAlerts, pollInterval);
    return () => clearInterval(interval);
  }, [fetchAlerts, pollInterval]);

  return { alerts, loading, error, refetch: fetchAlerts, deleteAlerts };
};  