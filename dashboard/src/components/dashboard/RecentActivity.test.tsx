import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { RecentActivity } from "./RecentActivity";

describe("RecentActivity", () => {
  it("renders the component title", () => {
    render(<RecentActivity />);
    expect(screen.getByText("最近活动")).toBeInTheDocument();
  });

  it("renders activity items from mock data", () => {
    render(<RecentActivity />);
    // Check for some known activity descriptions
    expect(screen.getByText(/买入 特朗普胜选 YES/)).toBeInTheDocument();
    expect(screen.getByText(/买入 比特币 > \$100k NO/)).toBeInTheDocument();
    expect(screen.getByText(/预测 特朗普胜选 75%/)).toBeInTheDocument();
  });

  it("renders time for each activity", () => {
    render(<RecentActivity />);
    // Check for known times from mock data
    expect(screen.getByText("10:30")).toBeInTheDocument();
    expect(screen.getByText("09:15")).toBeInTheDocument();
    expect(screen.getByText("09:00")).toBeInTheDocument();
  });

  it("renders amounts for trade activities", () => {
    render(<RecentActivity />);
    // Check for amount display ($10.00 and $8.00)
    expect(screen.getByText("$10.00")).toBeInTheDocument();
    expect(screen.getByText("$8.00")).toBeInTheDocument();
  });

  it("renders all activity items", () => {
    render(<RecentActivity />);
    // mockRecentActivity has 5 items
    const activityItems = screen.getAllByText(/\d{2}:\d{2}/);
    expect(activityItems).toHaveLength(5);
  });

  it("renders system activity without amount", () => {
    render(<RecentActivity />);
    expect(screen.getByText(/系统启动，开始扫描市场/)).toBeInTheDocument();
  });

  it("renders prediction activity without amount", () => {
    render(<RecentActivity />);
    expect(screen.getByText(/预测 比特币 > \$100k 35%/)).toBeInTheDocument();
  });
});
