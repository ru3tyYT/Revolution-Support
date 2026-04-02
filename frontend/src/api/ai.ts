import type { AskRequest, AskResponse } from "@/types";
import { apiClient } from "./client";

export const aiApi = {
  ask: async (request: AskRequest): Promise<AskResponse> => {
    const { data } = await apiClient.post<AskResponse>("/api/ai/ask", request);
    return data;
  },
};
