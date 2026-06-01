import axios from "axios";

// Base URL is build-time-inlined by Vite from VITE_API_URL. To change it after
// deploy you MUST redeploy - there is no runtime config. localhost is a dev
// fallback only.
const axiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? "http://localhost:5000",
});

// Request interceptor to attach token
axiosInstance.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem("token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Optional: Response interceptor to catch 401 errors globally
axiosInstance.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      console.error("Unauthorized - maybe redirect to login");
      // Example: window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);

export default axiosInstance;
