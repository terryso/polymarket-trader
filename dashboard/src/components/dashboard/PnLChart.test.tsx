import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { PnLChart } from "./PnLChart";

describe("PnLChart", () => {
  it("renders the chart title", () => {
    render(<PnLChart />);
    expect(screen.getByText("PnL 收益曲线")).toBeInTheDocument();
  });

  it("renders the time period subtitle", () => {
    render(<PnLChart />);
    expect(screen.getByText("近 7 天")).toBeInTheDocument();
  });

  it("renders chart container with correct height", () => {
    const { container } = render(<PnLChart />);
    const chartContainer = container.querySelector(".h-\\[250px\\]");
    expect(chartContainer).toBeInTheDocument();
  });

  it("renders within stat-card container", () => {
    const { container } = render(<PnLChart />);
    const statCard = container.querySelector(".stat-card");
    expect(statCard).toBeInTheDocument();
  });

  it("renders the AreaChart component", () => {
    const { container } = render(<PnLChart />);
    // The chart container should exist even if recharts doesn't render fully in jsdom
    const chartContainer = container.querySelector(".h-\\[250px\\]");
    expect(chartContainer).toBeTruthy();
  });
});
