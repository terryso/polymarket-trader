import {
  Home, BarChart3, History, Target, Settings, Bot, Sun, Moon,
} from "lucide-react";
import { NavLink } from "@/components/NavLink";
import { useLocation } from "react-router-dom";
import { mockStats } from "@/data/mockData";
import { useTheme } from "@/components/ThemeProvider";
import { Button } from "@/components/ui/button";
import {
  Sidebar, SidebarContent, SidebarGroup, SidebarGroupContent,
  SidebarMenu, SidebarMenuButton, SidebarMenuItem, SidebarFooter,
} from "@/components/ui/sidebar";

const navItems = [
  { title: "首页", url: "/", icon: Home },
  { title: "持仓", url: "/positions", icon: BarChart3 },
  { title: "交易历史", url: "/trades", icon: History },
  { title: "预测记录", url: "/predictions", icon: Target },
  { title: "设置", url: "/settings", icon: Settings },
];

export function AppSidebar() {
  const location = useLocation();
  const { theme, toggleTheme } = useTheme();

  const statusColor =
    mockStats.systemStatus === "running"
      ? "bg-profit"
      : mockStats.systemStatus === "paused"
      ? "bg-warning"
      : "bg-loss";

  return (
    <Sidebar className="border-r border-border">
      <div className="p-5 border-b border-border">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-primary/15 flex items-center justify-center">
            <Bot className="h-5 w-5 text-primary" />
          </div>
          <div className="flex-1 min-w-0">
            <h1 className="text-sm font-bold text-foreground tracking-tight">Polymarket</h1>
            <p className="text-xs text-muted-foreground">Trader Dashboard</p>
          </div>
          <Button variant="ghost" size="icon" onClick={toggleTheme} className="h-8 w-8 shrink-0 text-muted-foreground hover:text-foreground">
            {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
          </Button>
        </div>
      </div>

      <SidebarContent className="px-3 py-4">
        <SidebarGroup>
          <SidebarGroupContent>
            <SidebarMenu>
              {navItems.map((item) => (
                <SidebarMenuItem key={item.title}>
                  <SidebarMenuButton asChild>
                    <NavLink
                      to={item.url}
                      end={item.url === "/"}
                      className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground transition-colors"
                      activeClassName="bg-primary/10 text-primary font-medium"
                    >
                      <item.icon className="h-4 w-4 shrink-0" />
                      <span>{item.title}</span>
                    </NavLink>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter className="p-4 border-t border-border">
        <div className="space-y-2.5 text-xs">
          <div className="flex items-center justify-between">
            <span className="text-muted-foreground">模式</span>
            <span className="badge-paper">Paper</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-muted-foreground">资金</span>
            <span className="text-foreground font-mono font-medium">${mockStats.totalCapital.toFixed(2)}</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-muted-foreground">状态</span>
            <span className="flex items-center gap-1.5">
              <span className={`w-2 h-2 rounded-full ${statusColor} animate-pulse`} />
              <span className="text-foreground">运行中</span>
            </span>
          </div>
        </div>
      </SidebarFooter>
    </Sidebar>
  );
}
