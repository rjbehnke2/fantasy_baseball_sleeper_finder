"use client";

import { useEffect, useState } from "react";
import { getRankings } from "@/lib/api";
import { PlayerTable } from "@/components/players/player-table";
import type { RankedPlayer } from "@/lib/types";

export default function PlayersPage() {
  const [players, setPlayers] = useState<RankedPlayer[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getRankings({ limit: 500 })
      .then((data) => setPlayers(data.players))
      .catch((e) => { console.error("PlayersPage: API error:", e); setPlayers([]); })
      .finally(() => setLoading(false));
  }, []);

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Player Rankings</h1>
        <p className="text-sm text-gray-500 mt-1">
          AI-powered rankings sorted by composite value score. Click column headers to sort.
        </p>
      </div>

      {loading ? (
        <div className="bg-white rounded-lg border p-8 text-center text-gray-400">
          Loading rankings...
        </div>
      ) : (
        <PlayerTable players={players} />
      )}
    </div>
  );
}
