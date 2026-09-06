import { fireEvent, render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { StoryCardPage } from "./StoryCardPage";
import { api } from "@/api/endpoints";
import { useAuth } from "@/hooks/useAuth";

vi.mock("@/hooks/useAuth", () => ({ useAuth: vi.fn() }));
vi.mock("@/api/endpoints", () => ({ api: { storyCard: vi.fn() } }));
vi.mock("html-to-image", () => ({ toPng: vi.fn() }));

function LoginDestination() {
  const location = useLocation();
  return <p>Login for {location.state?.from}</p>;
}

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={["/story/CASE-1"]}>
        <Routes>
          <Route path="/story/:caseId" element={<StoryCardPage />} />
          <Route path="/login" element={<LoginDestination />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("story-card access and failures", () => {
  beforeEach(() => vi.resetAllMocks());

  it("redirects signed-out visitors and preserves the story destination", async () => {
    vi.mocked(useAuth).mockReturnValue({ loading: false, user: null } as ReturnType<typeof useAuth>);
    renderPage();
    expect(await screen.findByText("Login for /story/CASE-1")).toBeInTheDocument();
    expect(api.storyCard).not.toHaveBeenCalled();
  });

  it("does not request a story while authentication is loading", () => {
    vi.mocked(useAuth).mockReturnValue({ loading: true, user: null } as ReturnType<typeof useAuth>);
    renderPage();
    expect(api.storyCard).not.toHaveBeenCalled();
  });

  it("shows a retry action after a failed request", async () => {
    vi.mocked(useAuth).mockReturnValue({ loading: false, user: { id: "user-1" } } as ReturnType<typeof useAuth>);
    vi.mocked(api.storyCard).mockRejectedValue(new Error("Server unavailable"));
    renderPage();
    expect(await screen.findByRole("alert")).toHaveTextContent("Unable to load");
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(api.storyCard).toHaveBeenCalledTimes(2);
  });
});
