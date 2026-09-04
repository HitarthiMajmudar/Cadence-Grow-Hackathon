import { useRef, useState } from "react";
import { useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { toPng } from "html-to-image";
import { Download, Printer } from "lucide-react";
import { api } from "@/api/endpoints";
import { StoryCard } from "@/components/StoryCard";
import { Spinner } from "@/components/ui";

export function StoryCardPage() {
  const { caseId = "" } = useParams();
  const { data, isLoading } = useQuery({
    queryKey: ["story-card", caseId],
    queryFn: () => api.storyCard(caseId),
  });
  const ref = useRef<HTMLDivElement>(null);
  const [err, setErr] = useState<string | null>(null);

  const download = async () => {
    if (!ref.current) return;
    try {
      const url = await toPng(ref.current, { pixelRatio: 2, cacheBust: true });
      const a = document.createElement("a");
      a.href = url;
      a.download = `market-detective-${data?.symbol ?? "case"}.png`;
      a.click();
    } catch {
      setErr("PNG export not available in this browser — use Print instead.");
    }
  };

  return (
    <div className="grid min-h-screen place-items-center p-6">
      {isLoading || !data ? (
        <Spinner />
      ) : (
        <div className="space-y-4">
          <div className="flex justify-center">
            <StoryCard ref={ref} data={data} />
          </div>
          {err && <p className="text-center text-xs text-attention">{err}</p>}
          <div className="flex justify-center gap-2 print:hidden">
            <button className="btn-primary" onClick={download}>
              <Download className="h-4 w-4" /> Download PNG
            </button>
            <button className="btn-ghost" onClick={() => window.print()}>
              <Printer className="h-4 w-4" /> Print
            </button>
          </div>
          <p className="text-center text-[11px] text-slate-500 print:hidden">
            Educational market analysis. Not investment advice.
          </p>
        </div>
      )}
    </div>
  );
}
