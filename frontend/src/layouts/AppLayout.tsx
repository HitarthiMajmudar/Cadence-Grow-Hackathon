import { useEffect } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { Clock3, LayoutDashboard, ListChecks, LogOut, Search, Rewind } from "lucide-react";
import { useAuth } from "@/hooks/useAuth";
import { useHealth } from "@/hooks/queries";
import { OfflineDatasetBadge, DemoModeBadge } from "@/components/badges";
import { cx } from "@/utils/format";

const NAV = [
  { to: "/", label: "Investigation Room", icon: LayoutDashboard, end: true },
  { to: "/watchlists", label: "Watchlists", icon: ListChecks },
  { to: "/time-machine", label: "Time Machine", icon: Rewind },
  { to: "/stocks", label: "Stocks", icon: Search },
];

export function AppLayout() {
  const { user, loading, logout } = useAuth();
  const { data: health } = useHealth();
  const navigate = useNavigate();

  useEffect(() => {
    if (!loading && !user) navigate("/login", { replace: true });
  }, [loading, user, navigate]);

  if (loading || !user) {
    return (
      <div className="flex min-h-screen items-center justify-center text-slate-500">Loading…</div>
    );
  }

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-40 border-b border-white/10 bg-ink-950/80 backdrop-blur-xl">
        <div className="mx-auto flex max-w-[1400px] flex-wrap items-center gap-x-6 gap-y-3 px-4 py-3 lg:px-8">
          <NavLink to="/" className="flex items-center gap-2.5">
            <img src="/detective.svg" alt="" className="h-8 w-8" />
            <div className="leading-tight">
              <div className="text-sm font-extrabold tracking-tight">Market Detective</div>
              <div className="text-[10px] text-slate-500">Your stocks moved. We investigated why.</div>
            </div>
          </NavLink>

          <nav className="order-3 flex w-full items-center gap-1 overflow-x-auto scrollbar-thin lg:order-none lg:w-auto">
            {NAV.map(({ to, label, icon: Icon, end }) => (
              <NavLink
                key={to}
                to={to}
                end={end}
                className={({ isActive }) =>
                  cx(
                    "flex shrink-0 items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                    isActive ? "bg-white/10 text-white" : "text-slate-400 hover:bg-white/5 hover:text-slate-200",
                  )
                }
              >
                <Icon className="h-4 w-4" />
                {label}
              </NavLink>
            ))}
          </nav>

          <div className="ml-auto flex items-center gap-2">
            <div className="hidden items-center gap-2 sm:flex">
              <OfflineDatasetBadge label={health?.dataset_label} />
              <DemoModeBadge />
            </div>
            <div className="flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 py-1 pl-3 pr-1">
              <div className="text-right leading-tight">
                <div className="text-xs font-semibold">{user.name}</div>
                <div className="text-[10px] text-slate-500">{user.email}</div>
              </div>
              <button
                className="rounded-lg p-1.5 text-slate-400 hover:bg-white/10 hover:text-slate-200"
                title="Log out"
                onClick={() => {
                  logout();
                  navigate("/login");
                }}
              >
                <LogOut className="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-[1400px] px-4 py-6 lg:px-8">
        <Outlet />
      </main>

      <footer className="mx-auto max-w-[1400px] px-4 pb-10 pt-4 text-xs text-slate-600 lg:px-8">
        <div className="flex items-center gap-2">
          <Clock3 className="h-3.5 w-3.5" />
          {health?.db_backend === "mongo" ? "Persisted to MongoDB Atlas" : "Persisted to local file store"}
          {" · "}
          {health?.sentiment_model === "tfidf_logreg" ? "Local TF-IDF + LogReg sentiment" : "Rule-based sentiment"}
        </div>
        <p className="mt-1">
          Educational market-analysis prototype. Historical / synthetic data — <strong>not live market data</strong>.
          Nothing here is investment advice.
        </p>
      </footer>
    </div>
  );
}
