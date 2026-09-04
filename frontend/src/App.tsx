import { Navigate, Route, Routes } from "react-router-dom";
import { AppLayout } from "@/layouts/AppLayout";
import { LoginPage } from "@/pages/LoginPage";
import { DashboardPage } from "@/pages/DashboardPage";
import { StockDetailPage } from "@/pages/StockDetailPage";
import { CaseDetailPage } from "@/pages/CaseDetailPage";
import { TimeMachinePage } from "@/pages/TimeMachinePage";
import { WatchlistsPage } from "@/pages/WatchlistsPage";
import { StocksPage } from "@/pages/StocksPage";
import { StoryCardPage } from "@/pages/StoryCardPage";

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/story/:caseId" element={<StoryCardPage />} />
      <Route element={<AppLayout />}>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/watchlists" element={<WatchlistsPage />} />
        <Route path="/stocks" element={<StocksPage />} />
        <Route path="/stocks/:symbol" element={<StockDetailPage />} />
        <Route path="/cases/:caseId" element={<CaseDetailPage />} />
        <Route path="/time-machine" element={<TimeMachinePage />} />
        <Route path="/time-machine/:symbol" element={<TimeMachinePage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
