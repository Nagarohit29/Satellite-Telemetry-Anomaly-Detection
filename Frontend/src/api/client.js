import axios from "axios";

const client = axios.create({
  baseURL: "/api",
  timeout: 60000,
  headers: {
    "Content-Type": "application/json",
  },
});

export default client;