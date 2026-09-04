import { FormEvent, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Search, ShieldCheck, Sparkles } from "lucide-react";
import { useAuth } from "@/hooks/useAuth";
import { api } from "@/api/endpoints";
import type { User } from "@/types";
import { OfflineDatasetBadge } from "@/components/badges";

export function LoginPage() {
  const { user, login } = useAuth();
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [accounts, setAccounts] = useState<User[]>([]);

  useEffect(() => {
    if (user) navigate("/", { replace: true });
  }, [user, navigate]);

  useEffect(() => {
    api.demoAccounts().then(setAccounts).catch(() => setAccounts([]));
  }, []);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await login(name.trim(), email.trim());
      navigate("/", { replace: true });
    } catch (err: any) {
      setError(err?.message ?? "Could not sign in");
    } finally {
      setBusy(false);
    }
  }

  async function pickAccount(a: User) {
    setBusy(true);
    setError(null);
    try {
      await login(a.name, a.email);
      navigate("/", { replace: true });
    } catch (err: any) {
      setError(err?.message ?? "Could not sign in");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      <div className="relative hidden flex-col justify-between overflow-hidden border-r border-white/10 p-12 lg:flex">
        <div className="absolute -left-24 top-10 h-72 w-72 rounded-full bg-attention/20 blur-3xl" />
        <div className="absolute bottom-10 right-0 h-72 w-72 rounded-full bg-neutralc/20 blur-3xl" />
        <div className="relative flex items-center gap-3">
          <img src="/detective.svg" alt="" className="h-10 w-10" />
          <span className="text-lg font-extrabold tracking-tight">Market Detective</span>
        </div>
        <div className="relative space-y-6">
          <h1 className="text-4xl font-extrabold leading-tight">
            Your stocks moved.
            <br />
            <span className="text-attention">We investigated why.</span>
          </h1>
          <p className="max-w-md text-slate-400">
            Not a watchlist. Market Detective remembers what you last saw and turns the
            meaningful changes into evidence-backed Investigation Cases — then replays them in
            the Market Time Machine.
          </p>
          <ul className="space-y-2 text-sm text-slate-400">
            <li className="flex gap-2">
              <Sparkles className="h-4 w-4 text-attention" /> Unusual vs. normal, not just up vs. down
            </li>
            <li className="flex gap-2">
              <Search className="h-4 w-4 text-neutralc" /> Evidence Court: four detectives, one verdict
            </li>
            <li className="flex gap-2">
              <ShieldCheck className="h-4 w-4 text-gain" /> Honest about stale, missing & conflicting data
            </li>
          </ul>
        </div>
        <div className="relative">
          <OfflineDatasetBadge />
        </div>
      </div>

      <div className="flex items-center justify-center p-6">
        <div className="w-full max-w-sm space-y-6">
          <div className="lg:hidden">
            <div className="flex items-center gap-2.5">
              <img src="/detective.svg" alt="" className="h-9 w-9" />
              <span className="text-lg font-extrabold">Market Detective</span>
            </div>
          </div>

          <div>
            <h2 className="text-xl font-bold">Demo sign-in</h2>
            <p className="mt-1 text-sm text-slate-500">
              No passwords — this is a labelled demo. Return with the same email to keep your
              watchlists and snapshots.
            </p>
          </div>

          <form onSubmit={submit} className="space-y-3">
            <label className="block">
              <span className="label">Name</span>
              <input
                className="mt-1 w-full rounded-xl border border-white/10 bg-ink-850 px-3 py-2.5 text-sm outline-none focus:border-attention/60"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Ada Investigator"
                required
              />
            </label>
            <label className="block">
              <span className="label">Email</span>
              <input
                type="email"
                className="mt-1 w-full rounded-xl border border-white/10 bg-ink-850 px-3 py-2.5 text-sm outline-none focus:border-attention/60"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                required
              />
            </label>
            {error && <p className="text-sm text-risk">{error}</p>}
            <button className="btn-primary w-full" disabled={busy}>
              {busy ? "Signing in…" : "Enter the Investigation Room"}
            </button>
          </form>

          {accounts.length > 0 && (
            <div>
              <div className="label mb-2">Or open a seeded demo account</div>
              <div className="space-y-1.5">
                {accounts.map((a) => (
                  <button
                    key={a.id}
                    disabled={busy}
                    onClick={() => pickAccount(a)}
                    className="flex w-full items-center justify-between rounded-xl border border-white/10 bg-white/5 px-3 py-2.5 text-left text-sm hover:bg-white/10"
                  >
                    <span>
                      <span className="font-semibold">{a.name}</span>
                      <span className="ml-2 text-xs text-slate-500">{a.email}</span>
                    </span>
                    <span className="text-xs text-neutralc-soft">Open →</span>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
