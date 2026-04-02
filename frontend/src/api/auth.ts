import type { AdminCheck, UserResponse } from "@/types";
import { apiClient } from "./client";

export const authApi = {
  login: () => {
    const base = apiClient.defaults.baseURL || "";
    window.location.href = `${base}/api/auth/login`;
  },

  logout: async () => {
    await apiClient.post("/api/auth/logout");
    localStorage.removeItem("access_token");
  },

  getMe: async (): Promise<UserResponse> => {
    const { data } = await apiClient.get<UserResponse>("/api/auth/me");
    return data;
  },

  checkAdmin: async (): Promise<AdminCheck> => {
    const { data } = await apiClient.get<AdminCheck>("/api/auth/admin-check");
    return data;
  },
};
