"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { getPlayer } from "@/lib/api";
import type { PlayerDetail } from "@/lib/types";
import { ScoutingReportDisplay } from "@/components/players/scouting-report";
import { StatTrendChart } from "@/components/charts/stat-trend";
import { DynastyTrajectoryChart } from "@/components/charts/dynasty-trajectory";
import { ScoreBadge } from "@/components/ui/score-badge";
import { DollarBadge } from "@/components/ui/dollar-badge";
import { formatStat, formatPct, cn } from "@/lib/utils";

export default function PlayerDetailPage() {
  const params = useParams();
  const playerId = Number(params.playerId);
  const [player, setPlayer] = useState<PlayerDetail | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!playerId) return;
    getPlayer(playerId)
      .then(setPlayer)
      .catch((e) => { console.error("PlayerDetail: API error:", e); setPlayer(null); })
      .finally(() => setLoading(false));
  }, [playerId]);

  if (loading) {
    return (
      <div className="animate-pulse space-y-4">
        <div className="h-8 bg-gray-200 rounded w-1/3" />
        <div className="h-4 bg-gray-200 rounded w-1/4" />
        <div className="h-64 bg-gray-200 rounded" />
      </div>
    );
  }

  if (!player) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500">Player not found</p>
        <Link href="/players" className="text-blue-600 text-sm mt-2 inline-block">
          Back to rankings
        </Link>
      </div>
    );
  }

  const proj = player.projection;
  const isBatter = player.batting_seasons.length > 0;
  const isPitcher = player.pitching_seasons.length > 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <Link href="/players" className="text-xs text-blue-600 hover:underline">
            &larr; Back to rankings
          </Link>
          <h1 className="text-2xl font-bold text-gray-900 mt-1">{player.full_name}</h1>
          <p className="text-sm text-gray-500">
            {player.position} &middot; {player.team ?? "Free Agent"} &middot; Age {player.age ?? "?"}
            {player.status && player.status !== "active" && (
              <span className="ml-2 text-amber-600 font-medium">({player.status})</span>
            )}
          </p>
        </div>
        {proj && (
          <div className="text-right">
            <DollarBadge value={proj.auction_value} surplus={proj.surplus_value} size="lg" />
          </div>
        )}
      </div>

      {/* AI Scores Row */}
      {proj && (
        <div className="flex flex-wrap gap-3">
          <ScoreBadge label="AI Value" score={proj.ai_value_score} size="lg" />
          <ScoreBadge label="Sleeper" score={proj.sleeper_score} />
          <ScoreBadge label="Bust" score={proj.bust_score} />
          <ScoreBadge label="Consistency" score={proj.consistency_score} />
          <ScoreBadge label="Improvement" score={proj.improvement_score} />
          <ScoreBadge label="Dynasty" score={proj.dynasty_value} />
        </div>
      )}

      {/* Scouting Report — Hero Content */}
      <ScoutingReportDisplay playerId={playerId} />

      {/* Auction & Dynasty Card */}
      {proj && (
        <div className="bg-white rounded-lg border border-gray-200 p-5">
          <h3 className="font-semibold text-gray-900 mb-3">Auction & Dynasty Value</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <ValueCell label="Projected Value" value={`$${(proj.auction_value ?? 0).toFixed(0)}`} />
            <ValueCell label="Surplus Value" value={`$${(proj.surplus_value ?? 0).toFixed(0)}`}
              className={proj.surplus_value != null && proj.surplus_value > 0 ? "text-green-600" : "text-red-500"} />
            <ValueCell label="Dynasty Score" value={`${(proj.dynasty_value ?? 0).toFixed(1)}/100`} />
            <ValueCell label="Regression" value={
              proj.regression_direction != null
                ? `${proj.regression_direction > 0 ? "+" : ""}${proj.regression_direction.toFixed(3)}`
                : "—"
            } />
          </div>
        </div>
      )}

      {/* Dynasty Trajectory Chart */}
      <DynastyTrajectoryChart playerId={playerId} playerName={player.full_name} />

      {/* Stat Trend Charts */}
      {(isBatter || isPitcher) && (
        <StatTrendChart
          battingSeasons={isBatter ? player.batting_seasons : undefined}
          pitchingSeasons={isPitcher ? player.pitching_seasons : undefined}
        />
      )}

      {/* Batting Stats */}
      {isBatter && player.batting_seasons.length > 0 && (
        <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
          <h3 className="font-semibold text-gray-900 px-5 py-3 border-b border-gray-200">
            Batting History
          </h3>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 text-sm">
              <thead className="bg-gray-50">
                <tr>
                  {["Year", "PA", "AVG", "OBP", "SLG", "HR", "RBI", "SB", "wOBA", "xwOBA", "wRC+", "K%", "BB%", "Barrel%", "EV", "WAR"].map((h) => (
                    <th key={h} className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {player.batting_seasons.map((s) => (
                  <tr key={s.id} className="hover:bg-gray-50">
                    <td className="px-3 py-1.5 font-medium">{s.season}</td>
                    <td className="px-3 py-1.5">{s.pa ?? "—"}</td>
                    <td className="px-3 py-1.5 font-mono">{formatStat(s.avg)}</td>
                    <td className="px-3 py-1.5 font-mono">{formatStat(s.obp)}</td>
                    <td className="px-3 py-1.5 font-mono">{formatStat(s.slg)}</td>
                    <td className="px-3 py-1.5">{s.hr ?? "—"}</td>
                    <td className="px-3 py-1.5">{s.rbi ?? "—"}</td>
                    <td className="px-3 py-1.5">{s.sb ?? "—"}</td>
                    <td className="px-3 py-1.5 font-mono">{formatStat(s.woba)}</td>
                    <td className="px-3 py-1.5 font-mono">{formatStat(s.xwoba)}</td>
                    <td className="px-3 py-1.5">{s.wrc_plus ?? "—"}</td>
                    <td className="px-3 py-1.5 font-mono">{formatPct(s.k_pct)}</td>
                    <td className="px-3 py-1.5 font-mono">{formatPct(s.bb_pct)}</td>
                    <td className="px-3 py-1.5 font-mono">{formatPct(s.barrel_pct)}</td>
                    <td className="px-3 py-1.5 font-mono">{s.avg_exit_velocity != null ? s.avg_exit_velocity.toFixed(1) : "—"}</td>
                    <td className="px-3 py-1.5 font-mono">{s.war != null ? s.war.toFixed(1) : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Pitching Stats */}
      {isPitcher && player.pitching_seasons.length > 0 && (
        <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
          <h3 className="font-semibold text-gray-900 px-5 py-3 border-b border-gray-200">
            Pitching History
          </h3>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 text-sm">
              <thead className="bg-gray-50">
                <tr>
                  {["Year", "IP", "ERA", "WHIP", "FIP", "SIERA", "K%", "BB%", "K-BB%", "SwStr%", "SO", "W", "SV", "WAR"].map((h) => (
                    <th key={h} className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {player.pitching_seasons.map((s) => (
                  <tr key={s.id} className="hover:bg-gray-50">
                    <td className="px-3 py-1.5 font-medium">{s.season}</td>
                    <td className="px-3 py-1.5">{s.ip != null ? s.ip.toFixed(1) : "—"}</td>
                    <td className="px-3 py-1.5 font-mono">{s.era != null ? s.era.toFixed(2) : "—"}</td>
                    <td className="px-3 py-1.5 font-mono">{s.whip != null ? s.whip.toFixed(2) : "—"}</td>
                    <td className="px-3 py-1.5 font-mono">{s.fip != null ? s.fip.toFixed(2) : "—"}</td>
                    <td className="px-3 py-1.5 font-mono">{s.siera != null ? s.siera.toFixed(2) : "—"}</td>
                    <td className="px-3 py-1.5 font-mono">{formatPct(s.k_pct)}</td>
                    <td className="px-3 py-1.5 font-mono">{formatPct(s.bb_pct)}</td>
                    <td className="px-3 py-1.5 font-mono">{formatPct(s.k_bb_pct)}</td>
                    <td className="px-3 py-1.5 font-mono">{formatPct(s.swstr_pct)}</td>
                    <td className="px-3 py-1.5">{s.so ?? "—"}</td>
                    <td className="px-3 py-1.5">{s.w ?? "—"}</td>
                    <td className="px-3 py-1.5">{s.sv ?? "—"}</td>
                    <td className="px-3 py-1.5 font-mono">{s.war != null ? s.war.toFixed(1) : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

function ValueCell({ label, value, className }: { label: string; value: string; className?: string }) {
  return (
    <div>
      <p className="text-xs text-gray-500">{label}</p>
      <p className={cn("text-lg font-mono font-semibold", className)}>{value}</p>
    </div>
  );
}
