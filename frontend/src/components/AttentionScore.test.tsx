import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { AttentionScore, AttentionMeter } from "./AttentionScore";

describe("AttentionScore", () => {
  it("renders the rounded score and label", () => {
    render(<AttentionScore score={71.4} confidence={95} />);
    expect(screen.getByText("71")).toBeInTheDocument();
    expect(screen.getByText(/95% confidence/)).toBeInTheDocument();
    expect(screen.getByRole("img", { name: /score 71 of 100/i })).toBeInTheDocument();
  });

  it("clamps out-of-range scores", () => {
    render(<AttentionMeter score={140} />);
    expect(screen.getByText("100")).toBeInTheDocument();
  });
});
