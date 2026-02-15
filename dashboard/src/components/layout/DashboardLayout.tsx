import { ReactNode } from "react";
import { AppSidebar } from "./AppSidebar";
import { MobileNav } from "./MobileNav";
import { SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar";
import { Menu } from "lucide-react";

export function DashboardLayout({ children }: { children: ReactNode }) {
  return (
    <SidebarProvider>
      <div className="min-h-screen flex w-full">
        <AppSidebar />
        <main className="flex-1 min-w-0">
          <header className="h-14 flex items-center border-b border-border px-4 lg:hidden">
            <SidebarTrigger>
              <Menu className="h-5 w-5" />
            </SidebarTrigger>
          </header>
          <div className="p-4 md:p-6 lg:p-8 pb-20 lg:pb-8 animate-fade-in">
            {children}
          </div>
        </main>
        <MobileNav />
      </div>
    </SidebarProvider>
  );
}
