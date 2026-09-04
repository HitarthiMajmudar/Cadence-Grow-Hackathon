import { useRef, useState } from "react";
import { useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { toPng } from "html-to-image";
import { Download, Printer } from "lucide-react";
import { api } from "@/api/endpoints";
import { StoryCard } from "@/components/StoryCard";
import { Spinner } from "@/components/ui";
import {
  Artifact,
  ArtifactAction,
  ArtifactActions,
  ArtifactDescription,
  ArtifactHeader,
  ArtifactTitle,
  ArtifactContent,
} from "@/components/ai-elements/artifact";

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
    <div className="grid min-h-svh place-items-center bg-muted/30 p-6">
      {isLoading || !data ? (
        <Spinner />
      ) : (
        <Artifact className="w-full max-w-md">
          <ArtifactHeader>
            <div>
              <ArtifactTitle>Change Story Card</ArtifactTitle>
              <ArtifactDescription>
                {data.symbol} · educational market analysis, not investment advice
              </ArtifactDescription>
            </div>
            <ArtifactActions className="print:hidden">
              <ArtifactAction icon={Download} tooltip="Download PNG" onClick={download} />
              <ArtifactAction icon={Printer} tooltip="Print" onClick={() => window.print()} />
            </ArtifactActions>
          </ArtifactHeader>
          <ArtifactContent className="flex justify-center bg-muted/30">
            <StoryCard ref={ref} data={data} />
          </ArtifactContent>
          {err && (
            <p className="border-t px-4 py-2 text-center text-[11px] text-warning-foreground print:hidden">
              {err}
            </p>
          )}
        </Artifact>
      )}
    </div>
  );
}
