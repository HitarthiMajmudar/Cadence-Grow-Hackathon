import { useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { toPng } from "html-to-image";
import { Download, ExternalLink, Printer, X } from "lucide-react";
import { Link } from "react-router-dom";
import { api } from "@/api/endpoints";
import { StoryCard } from "./StoryCard";
import { Spinner } from "./ui";

export function StoryCardModal({ caseId, onClose }: { caseId: string; onClose: () => void }) {
  const { data, isLoading } = useQuery({
    queryKey: ["story-card", caseId],
    queryFn: () => api.storyCard(caseId),
  });
  const cardRef = useRef<HTMLDivElement>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const download = async () => {
    if (!cardRef.current) return;
    setBusy(true);
    setErr(null);
    try {
      const url = await toPng(cardRef.current, { pixelRatio: 2, cacheBust: true });
      const a = document.createElement("a");
      a.href = url;
      a.download = `market-detective-${data?.symbol ?? "case"}.png`;
      a.click();
    } catch {
      setErr("PNG export failed in this browser — use Print, or open the standalone card.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-ink-950/80 p-4 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="glass max-h-[92vh] w-full max-w-lg overflow-y-auto scrollbar-thin p-5"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-sm font-bold uppercase tracking-wide">Change Story Card</h3>
          <button className="rounded-lg p-1.5 text-slate-400 hover:bg-white/10" onClick={onClose}>
            <X className="h-4 w-4" />
          </button>
        </div>

        {isLoading || !data ? (
          <div className="grid h-64 place-items-center">
            <Spinner />
          </div>
        ) : (
          <>
            <div className="flex justify-center overflow-x-auto scrollbar-thin">
              <StoryCard ref={cardRef} data={data} />
            </div>
            {err && <p className="mt-3 text-xs text-attention">{err}</p>}
            <div className="mt-4 flex flex-wrap gap-2">
              <button className="btn-primary" onClick={download} disabled={busy}>
                <Download className="h-4 w-4" /> {busy ? "Rendering…" : "Download PNG"}
              </button>
              <button className="btn-ghost" onClick={() => window.print()}>
                <Printer className="h-4 w-4" /> Print
              </button>
              <Link to={`/story/${caseId}`} target="_blank" className="btn-ghost">
                <ExternalLink className="h-4 w-4" /> Open standalone
              </Link>
            </div>
            <p className="mt-3 text-[11px] text-slate-500">
              Renders entirely in your browser — no external service. {data.disclaimer}
            </p>
          </>
        )}
      </div>
    </div>
  );
}
