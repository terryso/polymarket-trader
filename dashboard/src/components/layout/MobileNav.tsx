import { Home, BarChart3, History, Target, Settings } from "lucide-react";
import { NavLink } from "@/components/NavLink";

const navItems = [
  { title: "首页", url: "/", icon: Home },
  { title: "持仓", url: "/positions", icon: BarChart3 },
  { title: "交易", url: "/trades", icon: History },
  { title: "预测", url: "/predictions", icon: Target },
  { title: "设置", url: "/settings", icon: Settings },
];

export function MobileNav() {
  return (
    <nav className="fixed bottom-0 left-0 right-0 z-50 bg-card border-t border-border lg:hidden">
      <div className="flex items-center justify-around h-14">
        {navItems.map((item) => (
          <NavLink
            key={item.title}
            to={item.url}
            end={item.url === "/"}
            className="flex flex-col items-center gap-0.5 px-2 py-1.5 text-muted-foreground transition-colors"
            activeClassName="text-primary"
          >
            <item.icon className="h-5 w-5" />
            <span className="text-[10px] font-medium">{item.title}</span>
          </NavLink>
        ))}
      </div>
    </nav>
  );
}
