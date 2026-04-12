import client from "./client";

export const predict = async (channel, data) => {
  const response = await client.post("/predict", { channel, data });
  return response.data;
};

export const getAlerts = async () => {
  const response = await client.get("/alerts");
  return response.data;
};

export const clearAlerts = async () => {
  const response = await client.delete("/alerts");
  return response.data;
};

export const getChannels = async () => {
  const response = await client.get("/channels");
  return response.data;
};

export const getBackendHealth = async () => {
  const response = await client.get("/backend/health");
  return response.data;
};

export const triggerTraining = async () => {
  const response = await client.post("/train");
  return response.data;
};