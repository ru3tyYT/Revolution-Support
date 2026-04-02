import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { DiscordGuild } from "@/types";

interface User {
  id: string;
  username: string;
  avatar?: string;
  guilds: DiscordGuild[];
  isAdmin: boolean;
  adminGuilds: DiscordGuild[];
}

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isAdmin: boolean;
  setUser: (user: User | null) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      isAuthenticated: false,
      isAdmin: false,
      setUser: (user) =>
        set({
          user,
          isAuthenticated: !!user,
          isAdmin: user?.isAdmin ?? false,
        }),
      logout: () =>
        set({
          user: null,
          isAuthenticated: false,
          isAdmin: false,
        }),
    }),
    { name: "auth-storage" },
  ),
);
