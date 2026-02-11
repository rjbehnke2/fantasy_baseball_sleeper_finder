"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getSleepers } from "@/lib/api";
import type { RankedPlayer } from "@/lib/types";
import { formatScore, formatDollar, scoreColor, surplusColor, cn } from "@/lib/utils";

export default function SleepersPage() {
  const [players, setPlayers] = useState<RankedPlayer[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getSleepers(50)
      .then((data) => setPlayers(data.players))
      .catch(() => setPlayers([]))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Sleeper Picks</h1>
        <p className="text-sm text-gray-500 mt-1">
          Players identified by AI as significantly undervalued. Strong underlying metrics at a discount price.
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
              className="bg-white rounded-lg border border-gray-200 border-l-4 border-l-green-500 p-5 hover:shadow-md transition-shadow"
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
                <div className={cn("text-2xl font-bold font-mono", scoreColor(player.sleeper_score))}>
                  {formatScore(player.sleeper_score)}
                </div>
              </div>

              <div className="mt-3 flex gap-4 text-sm">
                <div>
                  <span className="text-xs text-gray-500">Auction $</span>
                  <p className="font-mono">{formatDollar(player.auction_value)}</p>
                </div>
                <div>
                  <span className="text-xs text-gray-500">Surplus</span>
                  <p className={cn("font-mono", surplusColor(player.surplus_value))}>
                    {player.surplus_value != null ? `${player.surplus_value > 0 ? "+" : ""}${formatDollar(player.surplus_value)}` : "—"}
                  </p>
                </div>
                <div>
                  <span className="text-xs text-gray-500">AI Value</span>
                  <p className={cn("font-mono", scoreColor(player.ai_value_score))}>
                    {formatScore(player.ai_value_score)}
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
