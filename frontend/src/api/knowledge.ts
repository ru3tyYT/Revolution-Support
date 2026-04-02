import type { KnowledgeDoc, KnowledgeSearchResult } from "@/types";
import { apiClient } from "./client";

export const knowledgeApi = {
  listDocuments: async (guildId?: string): Promise<KnowledgeDoc[]> => {
    const params = guildId ? { guild_id: guildId } : {};
    const { data } = await apiClient.get<KnowledgeDoc[]>("/api/knowledge/documents", {
      params,
    });
    return data;
  },

  search: async (query: string, guildId?: string): Promise<KnowledgeSearchResult[]> => {
    const params: Record<string, string> = { query };
    if (guildId) params.guild_id = guildId;
    const { data } = await apiClient.get<KnowledgeSearchResult[]>("/api/knowledge/search", {
      params,
    });
    return data;
  },

  deleteDocument: async (docId: string) => {
    const { data } = await apiClient.delete(`/api/knowledge/documents/${docId}`);
    return data;
  },
};
