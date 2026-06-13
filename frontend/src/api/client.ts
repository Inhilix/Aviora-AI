import axios from "axios";

const api = axios.create({
  baseURL: "/api",
  withCredentials: true, // sends httpOnly JWT cookies automatically
  headers: { "Content-Type": "application/json" },
});

// Refresh token interceptor — retries once on 401
api.interceptors.response.use(
  (res) => res,
  async (err) => {
    const original = err.config;
    if (err.response?.status === 401 && !original._retried) {
      original._retried = true;
      try {
        await axios.post("/api/auth/refresh", {}, { withCredentials: true });
        return api(original);
      } catch {
        window.location.href = "/login";
      }
    }
    return Promise.reject(err);
  }
);

export default api;
