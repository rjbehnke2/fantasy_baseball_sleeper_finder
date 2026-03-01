"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getBusts } from "@/lib/api";
import type { RankedPlayer } from "@/lib/types";
import { formatScore, formatDollar, scoreColor, cn } from "@/lib/utils";

export default function BustsPage() {
  const [players, setPlayers] = useState<RankedPlayer[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getBusts(50)
      .then((data) => setPlayers(data.players))
      .catch((e) => { console.error("BustsPage: API error:", e); setPlayers([]); })
      .finally(() => setLoading(false));
  }, []);

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Bust Alerts</h1>
        <p className="text-sm text-gray-500 mt-1">
          Players flagged by AI for significant regression risk. Surface stats propped up by unsustainable luck.
        </p>
      </div>

      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="bg-white rounded-lg border p-5 animate-pulse">
              <div className="h-4 bg-gray-200 rounded w-1/2 mb-3" />
              <div className="h-3 bg-gray-200 rounded w-full mb-2" />
              <div className="h-3 bg-gray-200 rounded w-3/4" />
            </div>
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {players.map((player, i) => (
            <Link
              key={player.player_id}
              href={`/players/${player.player_id}`}
              className="bg-white rounded-lg border border-gray-200 border-l-4 border-l-red-500 p-5 hover:shadow-md transition-shadow"
            >
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono text-gray-400">#{i + 1}</span>
                    <h3 className="font-semibold text-gray-900">{player.full_name}</h3>
                  </div>
                  <p className="text-xs text-gray-500 mt-0.5">
                    {player.position} &middot; {player.team ?? "FA"} &middot; Age {player.age ?? "?"}
                  </p>
                </div>
                <div className="text-2xl font-bold font-mono text-red-500">
                  {formatScore(player.bust_score)}
                </div>
              </div>

              <div className="mt-3 flex gap-4 text-sm">
                <div>
                  <span className="text-xs text-gray-500">Auction $</span>
                  <p className="font-mono">{formatDollar(player.auction_value)}</p>
                </div>
                <div>
                  <span className="text-xs text-gray-500">Consistency</span>
                  <p className={cn("font-mono", scoreColor(player.consistency_score))}>
                    {formatScore(player.consistency_score)}
                  </p>
                </div>
                <div>
                  <span className="text-xs text-gray-500">Improvement</span>
                  <p className={cn("font-mono", player.improvement_score != null && player.improvement_score < -10 ? "text-red-500" : "text-gray-600")}>
                    {player.improvement_score != null ? `${player.improvement_score > 0 ? "+" : ""}${formatScore(player.improvement_score)}` : "—"}
                  </p>
                </div>
                <div>
                  <span className="text-xs text-gray-500">Dynasty</span>
                  <p className={cn("font-mono", scoreColor(player.dynasty_value))}>
                    {formatScore(player.dynasty_value)}
                  </p>
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
