import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AppSidebar } from "./AppSidebar";
import { ThemeProvider } from "@/components/ThemeProvider";
import { SidebarProvider } from "@/components/ui/sidebar";

// Mock localStorage
const localStorageMock = {
  getItem: vi.fn(() => "dark"),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
};
Object.defineProperty(window, "localStorage", { value: localStorageMock });

// Mock useOverview hook
vi.mock("@/hooks/useStatistics", () => ({
  useOverview: vi.fn(() => ({
    data: {
      mode: "PAPER",
      current_capital: 200.0,
      wallet_balance: null,
    },
  })),
}));

const renderWithProviders = (component: React.ReactNode) => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <ThemeProvider>
          <SidebarProvider>{component}</SidebarProvider>
        </ThemeProvider>
      </BrowserRouter>
    </QueryClientProvider>
  );
};

describe("AppSidebar", () => {
  it("renders the app title", () => {
    renderWithProviders(<AppSidebar />);
    expect(screen.getByText("Polymarket")).toBeInTheDocument();
    expect(screen.getByText("Trader Dashboard")).toBeInTheDocument();
  });

  it("renders all navigation items", () => {
    renderWithProviders(<AppSidebar />);
    expect(screen.getByText("首页")).toBeInTheDocument();
    expect(screen.getByText("持仓")).toBeInTheDocument();
    expect(screen.getByText("交易历史")).toBeInTheDocument();
    expect(screen.getByText("预测记录")).toBeInTheDocument();
    expect(screen.getByText("设置")).toBeInTheDocument();
  });

  it("renders mode display", () => {
    renderWithProviders(<AppSidebar />);
    expect(screen.getByText("模式")).toBeInTheDocument();
    expect(screen.getByText("Paper")).toBeInTheDocument();
  });

  it("renders wallet balance display", () => {
    renderWithProviders(<AppSidebar />);
    expect(screen.getByText("钱包余额")).toBeInTheDocument();
  });

  it("renders system capital display", () => {
    renderWithProviders(<AppSidebar />);
    expect(screen.getByText("系统记账")).toBeInTheDocument();
    // mockStats.totalCapital is 200.0
    expect(screen.getByText("$200.00")).toBeInTheDocument();
  });

  it("renders status indicator", () => {
    renderWithProviders(<AppSidebar />);
    expect(screen.getByText("状态")).toBeInTheDocument();
    expect(screen.getByText("运行中")).toBeInTheDocument();
  });

  it("renders theme toggle button", () => {
    renderWithProviders(<AppSidebar />);
    // Theme toggle button should be present
    const buttons = screen.getAllByRole("button");
    expect(buttons.length).toBeGreaterThan(0);
  });

  it("has correct navigation links", () => {
    renderWithProviders(<AppSidebar />);
    const homeLink = screen.getByRole("link", { name: /首页/ });
    expect(homeLink).toHaveAttribute("href", "/");

    const positionsLink = screen.getByRole("link", { name: /持仓/ });
    expect(positionsLink).toHaveAttribute("href", "/positions");
  });
});
