import { Button } from "@/components/ui/button";
import { LogOut } from "lucide-react";

export function LogoutButton() {
  return (
    <Button variant="ghost" className="text-white hover:bg-white/10" asChild>
      <a href="/auth/logout">
        <LogOut className="mr-2 h-4 w-4" />
        Logout
      </a>
    </Button>
  );
}
