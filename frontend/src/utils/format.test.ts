import { describe, expect, it } from "vitest";
import {
  changeClassMeta,
  compactNumber,
  marketHoursLabel,
  money,
  pct,
  priceDirClass,
  scoreColor,
  severityMeta,
  verdictTone,
} from "./format";

describe("format utilities", () => {
  it("formats money and handles null", () => {
    expect(money(1234.5)).toBe("₹1,234.5");
    expect(money(null)).toBe("—");
  });

  it("formats percentages with sign", () => {
    expect(pct(2.345)).toBe("+2.35%");
    expect(pct(-1.2)).toBe("-1.20%");
    expect(pct(null)).toBe("—");
  });

  it("compacts large numbers into Indian units", () => {
    expect(compactNumber(15_000_000)).toBe("1.50 Cr");
    expect(compactNumber(250_000)).toBe("2.50 L");
    expect(compactNumber(4200)).toBe("4.2k");
  });

  it("colours price direction", () => {
    expect(priceDirClass(1)).toContain("gain");
    expect(priceDirClass(-1)).toContain("risk");
    expect(priceDirClass(0)).toContain("slate");
  });

  it("maps attention score to a colour band", () => {
    expect(scoreColor(90)).toBe("#f43f5e");
    expect(scoreColor(65)).toBe("#f5a524");
    expect(scoreColor(10)).toBe("#64748b");
  });

  it("labels simulated market hours", () => {
    expect(marketHoursLabel(3)).toContain("3 simulated market hours");
    expect(marketHoursLabel(18)).toContain("~2.6 sessions");
    expect(marketHoursLabel(0)).toBe("just now");
  });

  it("classifies severities and change classes", () => {
    expect(severityMeta("critical").label).toBe("Critical");
    expect(severityMeta("minimal").label).toBe("Minimal");
    expect(changeClassMeta("important").label).toBe("Important");
    expect(changeClassMeta("insufficient_data").label).toBe("Insufficient data");
  });

  it("tones verdicts", () => {
    expect(verdictTone("Unusual price and volume activity")).toBe("risk");
    expect(verdictTone("Sector-driven movement")).toBe("neutral");
    expect(verdictTone("Normal movement")).toBe("muted");
  });
});
