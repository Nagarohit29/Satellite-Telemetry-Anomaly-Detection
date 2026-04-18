import client from "./client";

export const predict = async (channel, data, modelPreference = null) => {
  try {
    const payload = { channel, data };
    if (modelPreference) payload.model_preference = modelPreference;
    const response = await client.post("/predict", payload);
    return response.data;
  } catch (error) {
    console.error("Prediction API error:", error);
    throw new Error(`Failed to get prediction: ${error.message}`);
  }
};

export const getAlerts = async () => {
  try {
    const response = await client.get("/alerts");
    return response.data;
  } catch (error) {
    console.error("Get alerts API error:", error);
    throw new Error(`Failed to fetch alerts: ${error.message}`);
  }
};

export const clearAlerts = async () => {
  try {
    const response = await client.delete("/alerts");
    return response.data;
  } catch (error) {
    console.error("Clear alerts API error:", error);
    throw new Error(`Failed to clear alerts: ${error.message}`);
  }
};

export const getChannels = async () => {
  try {
    const response = await client.get("/channels");
    return response.data;
  } catch (error) {
    console.error("Get channels API error:", error);
    throw new Error(`Failed to fetch channels: ${error.message}`);
  }
};

export const getBackendHealth = async () => {
  try {
    const response = await client.get("/health");
    return response.data;
  } catch (error) {
    console.error("Health check API error:", error);
    throw new Error(`Failed to check health: ${error.message}`);
  }
};

export const triggerTraining = async (dataset = "SMAP", epochs = 5) => {
  try {
    const response = await client.post("/train", { dataset, epochs });
    return response.data;
  } catch (error) {
    console.error("Training API error:", error);
    throw new Error(`Failed to start training: ${error.message}`);
  }
};

export const sendChatMessage = async (messages, context = null, modelPreference = null) => {
  try {
    const payload = { messages, context };
    if (modelPreference) payload.model_preference = modelPreference;
    const response = await client.post("/chat", payload);
    return response.data;
  } catch (error) {
    console.error("Chat API error:", error);
    throw new Error(`Failed to send message: ${error.message}`);
  }
};

export const getLLMModels = async () => {
  try {
    const response = await client.get("/chat/models");
    return response.data;
  } catch (error) {
    console.error("Models API error:", error);
    throw new Error(`Failed to fetch models: ${error.message}`);
  }
};

export const updateAPIKey = async (provider, key) => {
  try {
    const response = await client.post("/config/keys", { provider, key });
    return response.data;
  } catch (error) {
    console.error("Update API key error:", error);
    throw new Error(`Failed to update API key: ${error.message}`);
  }
};

export const deleteAPIKey = async (provider) => {
  try {
    const response = await client.delete(`/config/keys/${provider}`);
    return response.data;
  } catch (error) {
    console.error("Delete API key error:", error);
    throw new Error(`Failed to delete API key: ${error.message}`);
  }
};