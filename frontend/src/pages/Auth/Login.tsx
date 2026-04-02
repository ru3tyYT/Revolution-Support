import { authApi } from "@/api/auth";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export function LoginPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-zinc-50">
      <Card className="w-[400px]">
        <CardHeader>
          <CardTitle className="text-center">Discord Support Bot</CardTitle>
        </CardHeader>
        <CardContent>
          <Button onClick={() => authApi.login()} className="w-full" size="lg">
            Login with Discord
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
