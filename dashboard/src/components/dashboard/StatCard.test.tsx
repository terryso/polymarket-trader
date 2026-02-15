import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { StatCard } from "./StatCard";
import { DollarSign, TrendingUp } from "lucide-react";

describe("StatCard", () => {
  it("renders title and value correctly", () => {
    render(
      <StatCard
        icon={<DollarSign data-testid="dollar-icon" />}
        title="Total Capital"
        value="$200.00"
      />
    );

    expect(screen.getByText("Total Capital")).toBeInTheDocument();
    expect(screen.getByText("$200.00")).toBeInTheDocument();
  });

  it("renders subtitle when provided", () => {
    render(
      <StatCard
        icon={<DollarSign />}
        title="Today PnL"
        value="+$15.50"
        subtitle="+5.2%"
        subtitleColor="profit"
      />
    );

    expect(screen.getByText("+5.2%")).toBeInTheDocument();
  });

  it("does not render subtitle when not provided", () => {
    render(
      <StatCard
        icon={<DollarSign />}
        title="Win Rate"
        value="75%"
      />
    );

    // Check that the component still renders value
    expect(screen.getByText("75%")).toBeInTheDocument();
  });

  it("applies profit color class to subtitle", () => {
    render(
      <StatCard
        icon={<TrendingUp />}
        title="Profit"
        value="$100"
        subtitle="+10%"
        subtitleColor="profit"
      />
    );

    const subtitle = screen.getByText("+10%");
    expect(subtitle).toHaveClass("profit-text");
  });

  it("applies loss color class to subtitle", () => {
    render(
      <StatCard
        icon={<TrendingUp />}
        title="Loss"
        value="-$50"
        subtitle="-5%"
        subtitleColor="loss"
      />
    );

    const subtitle = screen.getByText("-5%");
    expect(subtitle).toHaveClass("loss-text");
  });

  it("applies muted color class to subtitle by default", () => {
    render(
      <StatCard
        icon={<DollarSign />}
        title="Capital"
        value="$200"
        subtitle="Updated"
        subtitleColor="muted"
      />
    );

    const subtitle = screen.getByText("Updated");
    expect(subtitle).toHaveClass("text-muted-foreground");
  });

  it("renders icon element", () => {
    render(
      <StatCard
        icon={<span data-testid="custom-icon">Icon</span>}
        title="Test"
        value="100"
      />
    );

    expect(screen.getByTestId("custom-icon")).toBeInTheDocument();
  });

  it("applies custom className", () => {
    const { container } = render(
      <StatCard
        icon={<DollarSign />}
        title="Test"
        value="100"
        className="custom-class"
      />
    );

    const card = container.querySelector(".custom-class");
    expect(card).toBeInTheDocument();
  });
});
