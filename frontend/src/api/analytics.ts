import type { AnalyticsSummary } from "@/types";
import { apiClient } from "./client";

export const analyticsApi = {
  getSummary: async (guildId?: string, days = 7): Promise<AnalyticsSummary> => {
    const params: Record<string, string> = { days: String(days) };
    if (guildId) params.guild_id = guildId;
    const { data } = await apiClient.get<AnalyticsSummary>("/api/analytics/summary", {
      params,
    });
    return data;
  },

  getQueryLogs: async (guildId?: string, responseType?: string) => {
    const params: Record<string, string> = {};
    if (guildId) params.guild_id = guildId;
    if (responseType) params.response_type = responseType;
    const { data } = await apiClient.get("/api/analytics/queries", { params });
    return data;
  },
};
