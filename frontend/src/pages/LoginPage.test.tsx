import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { LoginPage } from "./LoginPage";

vi.mock("@/hooks/useAuth", () => ({
  useAuth: () => ({ user: { id: "signed-in" } }),
}));

describe("login destination", () => {
  it.each([
    ["/story/CASE-1", "Story destination"],
    ["//example.com", "Dashboard destination"],
    ["/\\example.com", "Dashboard destination"],
    ["/login", "Dashboard destination"],
  ])("handles %s", async (from, expected) => {
    render(
      <MemoryRouter initialEntries={[{ pathname: "/login", state: { from } }]}>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/story/CASE-1" element={<p>Story destination</p>} />
          <Route path="/" element={<p>Dashboard destination</p>} />
        </Routes>
      </MemoryRouter>,
    );
    expect(await screen.findByText(expected)).toBeInTheDocument();
  });
});
