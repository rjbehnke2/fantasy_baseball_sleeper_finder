"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getSleepers, getBusts, getRankings } from "@/lib/api";
import type { RankedPlayer } from "@/lib/types";
import { formatScore, formatDollar, scoreColor, surplusColor, cn } from "@/lib/utils";

export default function Dashboard() {
  const [sleepers, setSleepers] = useState<RankedPlayer[]>([]);
  const [busts, setBusts] = useState<RankedPlayer[]>([]);
  const [topValues, setTopValues] = useState<RankedPlayer[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      getSleepers(5).catch(() => ({ players: [] })),
      getBusts(5).catch(() => ({ players: [] })),
      getRankings({ limit: 5 }).catch(() => ({ players: [] })),
    ]).then(([s, b, v]) => {
      setSleepers(s.players);
      setBusts(b.players);
      setTopValues(v.players);
      setLoading(false);
    });
  }, []);

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-sm text-gray-500 mt-1">
          AI-powered dynasty auction analysis
        </p>
      </div>

      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {[1, 2, 3].map((i) => (
            <div key={i} className="bg-white rounded-lg border p-6 animate-pulse">
              <div className="h-4 bg-gray-200 rounded w-1/2 mb-4" />
              <div className="space-y-3">
                <div className="h-3 bg-gray-200 rounded" />
                <div className="h-3 bg-gray-200 rounded" />
                <div className="h-3 bg-gray-200 rounded" />
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Top Sleepers */}
          <DashboardCard
            title="Top Sleepers"
            subtitle="Undervalued players with upside"
            linkHref="/sleepers"
            linkLabel="View all sleepers"
            accentColor="green"
          >
            {sleepers.map((p) => (
              <PlayerRow
                key={p.player_id}
                player={p}
                scoreLabel="Sleeper"
                scoreValue={p.sleeper_score}
              />
            ))}
          </DashboardCard>

          {/* Bust Alerts */}
          <DashboardCard
            title="Bust Alerts"
            subtitle="Overvalued regression candidates"
            linkHref="/busts"
            linkLabel="View all busts"
            accentColor="red"
          >
            {busts.map((p) => (
              <PlayerRow
                key={p.player_id}
                player={p}
                scoreLabel="Bust"
                scoreValue={p.bust_score}
              />
            ))}
          </DashboardCard>

          {/* Best Values */}
          <DashboardCard
            title="Best Auction Values"
            subtitle="Highest surplus value"
            linkHref="/players"
            linkLabel="View full rankings"
            accentColor="blue"
          >
            {topValues.map((p) => (
              <div key={p.player_id} className="flex items-center justify-between py-1.5">
                <Link
                  href={`/players/${p.player_id}`}
                  className="text-sm font-medium text-gray-900 hover:text-blue-600"
                >
                  {p.full_name}
                  <span className="text-xs text-gray-400 ml-1">{p.position}</span>
                </Link>
                <div className="text-right">
                  <span className="text-sm font-mono">{formatDollar(p.auction_value)}</span>
                  {p.surplus_value != null && (
                    <span className={cn("text-xs font-mono ml-1", surplusColor(p.surplus_value))}>
                      ({p.surplus_value > 0 ? "+" : ""}{formatDollar(p.surplus_value)})
                    </span>
                  )}
                </div>
              </div>
            ))}
          </DashboardCard>
        </div>
      )}
    </div>
  );
}

function DashboardCard({
  title,
  subtitle,
  linkHref,
  linkLabel,
  accentColor,
  children,
}: {
  title: string;
  subtitle: string;
  linkHref: string;
  linkLabel: string;
  accentColor: "green" | "red" | "blue";
  children: React.ReactNode;
}) {
  const borderColors = {
    green: "border-t-green-500",
    red: "border-t-red-500",
    blue: "border-t-blue-500",
  };

  return (
    <div className={cn("bg-white rounded-lg border border-gray-200 border-t-4", borderColors[accentColor])}>
      <div className="px-5 py-4 border-b border-gray-100">
        <h2 className="font-semibold text-gray-900">{title}</h2>
        <p className="text-xs text-gray-500">{subtitle}</p>
      </div>
      <div className="px-5 py-3 divide-y divide-gray-50">
        {children}
      </div>
      <div className="px-5 py-3 border-t border-gray-100">
        <Link href={linkHref} className="text-xs text-blue-600 hover:text-blue-800 font-medium">
          {linkLabel} &rarr;
        </Link>
      </div>
    </div>
  );
}

function PlayerRow({
  player,
  scoreLabel,
  scoreValue,
}: {
  player: RankedPlayer;
  scoreLabel: string;
  scoreValue: number | null;
}) {
  return (
    <div className="flex items-center justify-between py-1.5">
      <Link
        href={`/players/${player.player_id}`}
        className="text-sm font-medium text-gray-900 hover:text-blue-600"
      >
        {player.full_name}
        <span className="text-xs text-gray-400 ml-1">{player.position}</span>
      </Link>
      <span className={cn("text-sm font-mono font-semibold", scoreColor(scoreValue))}>
        {formatScore(scoreValue)}
      </span>
    </div>
  );
}
