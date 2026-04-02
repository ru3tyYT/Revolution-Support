import type { ReactNode } from "react";
import { authApi } from "@/api/auth";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { useAuthStore } from "@/stores/authStore";

interface LayoutProps {
  children: ReactNode;
}

export function Layout({ children }: LayoutProps) {
  const { user, logout } = useAuthStore();

  const handleLogout = async () => {
    await authApi.logout();
    logout();
    localStorage.removeItem("access_token");
    window.location.href = "/login";
  };

  return (
    <div className="min-h-screen bg-zinc-50">
      <header className="flex items-center justify-between border-b border-zinc-200 bg-white px-6 py-4">
        <h1 className="text-xl font-semibold">Support Bot</h1>
        <div className="flex items-center gap-4">
          <span className="text-sm text-zinc-600">{user?.username}</span>
          <Avatar>
            <AvatarImage
              src={
                user?.avatar
                  ? `https://cdn.discordapp.com/avatars/${user.id}/${user.avatar}.png`
                  : undefined
              }
            />
            <AvatarFallback>{user?.username?.[0]?.toUpperCase()}</AvatarFallback>
          </Avatar>
          <Button variant="outline" size="sm" onClick={handleLogout}>
            Logout
          </Button>
        </div>
      </header>
      <main>{children}</main>
    </div>
  );
}
