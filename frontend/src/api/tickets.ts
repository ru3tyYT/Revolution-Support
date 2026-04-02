import type { Ticket } from "@/types";
import { apiClient } from "./client";

export const ticketsApi = {
  list: async (): Promise<Ticket[]> => {
    const { data } = await apiClient.get<Ticket[]>("/api/tickets");
    return data;
  },

  get: async (ticketId: string): Promise<Ticket> => {
    const { data } = await apiClient.get<Ticket>(`/api/tickets/${ticketId}`);
    return data;
  },
};
