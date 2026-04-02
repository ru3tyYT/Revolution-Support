import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { authApi } from "@/api/auth";
import { useAuthStore } from "@/stores/authStore";
import type { DiscordGuild } from "@/types";

export function AuthCallbackPage() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const setUser = useAuthStore((s) => s.setUser);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token = params.get("token");
    if (!token) {
      navigate("/login", { replace: true });
      return;
    }
    localStorage.setItem("access_token", token);

    (async () => {
      try {
        const me = await authApi.getMe();
        const admin = await authApi.checkAdmin();
        setUser({
          id: me.discord_id,
          username: me.username,
          avatar: me.avatar,
          guilds: me.guilds as DiscordGuild[],
          isAdmin: admin.is_admin,
          adminGuilds: admin.admin_guilds as DiscordGuild[],
        });
        navigate(admin.is_admin ? "/admin" : "/portal", { replace: true });
      } catch {
        localStorage.removeItem("access_token");
        setError("Could not complete sign-in.");
        navigate("/login", { replace: true });
      }
    })();
  }, [params, navigate, setUser]);

  if (error) {
    return <div className="p-6 text-center text-red-600">{error}</div>;
  }

  return <div className="p-6 text-center text-zinc-600">Signing you in…</div>;
}
