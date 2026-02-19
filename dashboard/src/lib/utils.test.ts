import { describe, it, expect } from "vitest";
import { cn } from "./utils";

describe("cn utility", () => {
  it("merges class names correctly", () => {
    const result = cn("class1", "class2");
    expect(result).toBe("class1 class2");
  });

  it("handles conditional classes", () => {
    const result = cn("base", false && "hidden", "visible");
    expect(result).toBe("base visible");
  });

  it("handles undefined and null values", () => {
    const result = cn("base", undefined, null, "end");
    expect(result).toBe("base end");
  });

  it("merges tailwind classes correctly", () => {
    // tailwind-merge should handle conflicting classes
    const result = cn("p-4", "p-2");
    expect(result).toBe("p-2");
  });

  it("handles object syntax", () => {
    const result = cn({
      active: true,
      disabled: false,
      visible: true,
    });
    expect(result).toContain("active");
    expect(result).toContain("visible");
    expect(result).not.toContain("disabled");
  });

  it("handles array syntax", () => {
    const result = cn(["class1", "class2"], "class3");
    expect(result).toContain("class1");
    expect(result).toContain("class2");
    expect(result).toContain("class3");
  });

  it("handles empty input", () => {
    const result = cn();
    expect(result).toBe("");
  });
});
