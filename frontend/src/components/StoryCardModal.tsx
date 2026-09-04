import { useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { toPng } from "html-to-image";
import { Download, ExternalLink, Printer } from "lucide-react";
import { Link } from "react-router-dom";
import { api } from "@/api/endpoints";
import { StoryCard } from "./StoryCard";
import { Spinner } from "./ui";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button, buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

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
      a.download = `cadence-${data?.symbol ?? "case"}.png`;
      a.click();
    } catch {
      setErr("PNG export failed in this browser — use Print, or open the standalone card.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Change Story Card</DialogTitle>
        </DialogHeader>

        {isLoading || !data ? (
          <div className="grid h-64 place-items-center">
            <Spinner />
          </div>
        ) : (
          <>
            <div className="flex justify-center overflow-x-auto">
              <StoryCard ref={cardRef} data={data} />
            </div>
            {err && <p className="text-xs text-warning-foreground">{err}</p>}
            <div className="flex flex-wrap gap-2">
              <Button size="sm" onClick={download} disabled={busy}>
                <Download /> {busy ? "Rendering…" : "Download PNG"}
              </Button>
              <Button variant="outline" size="sm" onClick={() => window.print()}>
                <Printer /> Print
              </Button>
              <Link
                to={`/story/${caseId}`}
                target="_blank"
                className={cn(buttonVariants({ variant: "outline", size: "sm" }), "gap-1.5")}
              >
                <ExternalLink /> Open standalone
              </Link>
            </div>
            <p className="text-[11px] text-muted-foreground">
              Renders entirely in your browser — no external service. {data.disclaimer}
            </p>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}
