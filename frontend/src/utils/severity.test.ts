import { describe, expect, it } from "vitest";
import { riskBand, severityClass } from "./severity";

describe("severity utils", () => {
  it("maps risk scores to bands", () => {
    expect(riskBand(91)).toBe("critical");
    expect(riskBand(70)).toBe("high");
    expect(riskBand(50)).toBe("medium");
    expect(riskBand(20)).toBe("low");
    expect(riskBand(5)).toBe("info");
  });

  it("returns a class for every severity and falls back safely", () => {
    expect(severityClass("critical")).toContain("red");
    expect(severityClass("high")).toContain("orange");
    expect(severityClass("medium")).toContain("amber");
    expect(severityClass("low")).toContain("sky");
    expect(severityClass(null)).toContain("slate"); // info fallback
    // an unknown value degrades to a neutral style, never throws
    expect(typeof severityClass("bogus")).toBe("string");
    expect(severityClass("bogus").length).toBeGreaterThan(0);
  });
});
