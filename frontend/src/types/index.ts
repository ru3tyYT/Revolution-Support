export interface DiscordGuild {
  id: string;
  name: string;
  icon?: string;
}

export interface UserResponse {
  discord_id: string;
  username: string;
  avatar?: string;
  guilds: DiscordGuild[];
}

export interface AdminCheck {
  is_admin: boolean;
  admin_guilds: DiscordGuild[];
}

export interface AnalyticsSummary {
  total_queries: number;
  successful_queries: number;
  failed_queries: number;
  average_response_time_ms: number;
  cost_total: number;
  top_keywords: Array<{ keyword: string; count: number }>;
  response_type_breakdown: Record<string, number>;
}

export interface KnowledgeDoc {
  id: string;
  title: string;
  source?: string;
  doc_type: string;
  created_at: string;
  is_processed: boolean;
}

export interface KnowledgeSearchResult {
  id: string;
  title: string;
  content: string;
  score: number;
}

export interface Ticket {
  id: string;
  user_id: string;
  guild_id: string;
  channel_id: string;
  status: string;
  created_at: string;
  updated_at: string;
  messages: Array<{
    role: string;
    content: string;
    timestamp?: string;
  }>;
}

export interface AskRequest {
  question: string;
  guild_id?: string;
}

export interface AskResponse {
  answer: string;
  confidence: number;
  sources: string[];
  response_type: string;
}
