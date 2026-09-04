import { FormEvent, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Search, ShieldCheck, Sparkles } from "lucide-react";
import { useAuth } from "@/hooks/useAuth";
import { api } from "@/api/endpoints";
import type { User } from "@/types";
import { OfflineDatasetBadge } from "@/components/badges";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

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
    <div className="grid min-h-svh lg:grid-cols-2">
      <div className="hidden flex-col justify-between border-r bg-muted/30 p-12 lg:flex">
        <div className="flex items-center gap-3">
          <img src="/detective.svg" alt="" className="size-9" />
          <span className="text-lg font-semibold tracking-tight">Market Detective</span>
        </div>
        <div className="space-y-6">
          <h1 className="text-3xl font-semibold leading-tight tracking-tight">
            Your stocks moved.
            <br />
            We investigated why.
          </h1>
          <p className="max-w-md text-sm text-muted-foreground">
            Not a watchlist. Market Detective remembers what you last saw and turns the meaningful
            changes into evidence-backed Investigation Cases — then replays them in the Market Time
            Machine.
          </p>
          <ul className="space-y-2 text-sm text-muted-foreground">
            <li className="flex items-center gap-2">
              <Sparkles className="size-4 text-primary" /> Unusual vs. normal, not just up vs. down
            </li>
            <li className="flex items-center gap-2">
              <Search className="size-4 text-primary" /> Evidence Court: four detectives, one verdict
            </li>
            <li className="flex items-center gap-2">
              <ShieldCheck className="size-4 text-primary" /> Honest about stale, missing &
              conflicting data
            </li>
          </ul>
        </div>
        <OfflineDatasetBadge />
      </div>

      <div className="flex items-center justify-center p-6">
        <div className="w-full max-w-sm space-y-6">
          <div className="lg:hidden">
            <div className="flex items-center gap-2.5">
              <img src="/detective.svg" alt="" className="size-8" />
              <span className="text-lg font-semibold">Market Detective</span>
            </div>
          </div>

          <div>
            <h2 className="text-lg font-semibold tracking-tight">Demo sign-in</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              No passwords — this is a labelled demo. Return with the same email to keep your
              watchlists and snapshots.
            </p>
          </div>

          <form onSubmit={submit} className="space-y-3">
            <div className="space-y-1.5">
              <Label htmlFor="name">Name</Label>
              <Input
                id="name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Ada Investigator"
                required
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                required
              />
            </div>
            {error && <p className="text-xs text-destructive">{error}</p>}
            <Button type="submit" className="w-full" disabled={busy}>
              {busy ? "Signing in…" : "Enter the Investigation Room"}
            </Button>
          </form>

          {accounts.length > 0 && (
            <div>
              <div className="mb-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">
                Or open a seeded demo account
              </div>
              <div className="space-y-1.5">
                {accounts.map((a) => (
                  <Button
                    key={a.id}
                    variant="outline"
                    disabled={busy}
                    onClick={() => pickAccount(a)}
                    className="h-auto w-full justify-between py-2"
                  >
                    <span className="font-medium">{a.name}</span>
                    <span className="text-xs text-muted-foreground">{a.email}</span>
                  </Button>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
