import axios from "axios";

const API_TIMEOUT_MS = Number(import.meta.env.VITE_API_TIMEOUT_MS || 180000);

const client = axios.create({
  baseURL: "/api",
  timeout: API_TIMEOUT_MS,
  headers: {
    "Content-Type": "application/json",
  },
});

export default client;
