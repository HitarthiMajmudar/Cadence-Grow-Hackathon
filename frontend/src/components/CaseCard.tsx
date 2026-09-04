import { Link } from "react-router-dom";
import { ArrowUpRight, Clock, Eye, Users } from "lucide-react";
import type { CaseSummary } from "@/types";
import { AttentionMeter } from "./AttentionScore";
import { Sparkline } from "./Sparkline";
import { VerdictBadge } from "./badges";
import { Chip } from "./ui";
import { cx, fmtDateTime, severityMeta } from "@/utils/format";

export function CaseCard({ c, dense = false }: { c: CaseSummary; dense?: boolean }) {
  const sev = severityMeta(c.severity);
  return (
    <Link
      to={`/cases/${c.case_id}`}
      className={cx(
        "group block glass card-hover p-4 transition-colors hover:border-white/20",
        !c.is_seen && "ring-1 ring-attention/25",
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-mono text-sm font-bold text-slate-100">{c.symbol}</span>
            <span className="truncate text-xs text-slate-500">{c.company_name}</span>
            {!c.is_seen && <span className="h-1.5 w-1.5 rounded-full bg-attention" title="New since your last visit" />}
          </div>
          <div className="mt-1.5">
            <VerdictBadge verdict={c.verdict} />
          </div>
        </div>
        <ArrowUpRight className="h-4 w-4 shrink-0 text-slate-600 transition-colors group-hover:text-slate-300" />
      </div>

      <p className={cx("mt-2 text-sm text-slate-300", dense ? "line-clamp-2" : "line-clamp-3")}>
        {c.headline_explanation}
      </p>

      <div className="mt-3 flex items-center justify-between gap-3">
        <AttentionMeter score={c.attention_score} />
        <Sparkline data={c.spark ?? []} width={70} height={22} />
      </div>

      <div className="mt-2 flex flex-wrap items-center gap-1.5 text-[11px] text-slate-500">
        <Chip className={cx(sev.cls, "!py-0.5")}>{sev.label}</Chip>
        <span className="flex items-center gap-1">
          <Clock className="h-3 w-3" />
          {fmtDateTime(c.detection_timestamp)}
        </span>
        {c.status === "viewed" && (
          <span className="flex items-center gap-1">
            <Eye className="h-3 w-3" /> viewed
          </span>
        )}
        {typeof c.peers_in_move === "number" && c.peers_in_move > 0 && (
          <span className="flex items-center gap-1">
            <Users className="h-3 w-3" /> +{c.peers_in_move} peers
          </span>
        )}
        <span className="ml-auto">{Math.round(c.confidence)}% conf</span>
      </div>
    </Link>
  );
}
