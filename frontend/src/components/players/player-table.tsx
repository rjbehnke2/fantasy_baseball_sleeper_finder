"use client";

import { useState } from "react";
import Link from "next/link";
import type { RankedPlayer } from "@/lib/types";
import { formatScore, formatDollar, formatPct, scoreColor, surplusColor, cn } from "@/lib/utils";

interface PlayerTableProps {
  players: RankedPlayer[];
  showSleeper?: boolean;
  showBust?: boolean;
}

type SortKey = keyof RankedPlayer;

export function PlayerTable({ players, showSleeper = true, showBust = true }: PlayerTableProps) {
  const [sortKey, setSortKey] = useState<SortKey>("ai_value_score");
  const [sortAsc, setSortAsc] = useState(false);
  const [posFilter, setPosFilter] = useState<string>("");

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortAsc(!sortAsc);
    } else {
      setSortKey(key);
      setSortAsc(false);
    }
  };

  const filtered = posFilter
    ? players.filter((p) => p.position?.includes(posFilter))
    : players;

  const sorted = [...filtered].sort((a, b) => {
    const aVal = a[sortKey] ?? -999;
    const bVal = b[sortKey] ?? -999;
    if (aVal < bVal) return sortAsc ? -1 : 1;
    if (aVal > bVal) return sortAsc ? 1 : -1;
    return 0;
  });

  const SortHeader = ({ label, colKey }: { label: string; colKey: SortKey }) => (
    <th
      className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:text-gray-900 select-none"
      onClick={() => handleSort(colKey)}
    >
      {label}
      {sortKey === colKey && (
        <span className="ml-1">{sortAsc ? "\u25B2" : "\u25BC"}</span>
      )}
    </th>
  );

  const positions = ["C", "1B", "2B", "SS", "3B", "OF", "SP", "RP", "DH"];

  return (
    <div>
      {/* Position filter */}
      <div className="flex gap-1 mb-3 flex-wrap">
        <button
          className={cn(
            "px-2 py-1 text-xs rounded-md border",
            !posFilter ? "bg-gray-900 text-white border-gray-900" : "bg-white text-gray-600 border-gray-300 hover:bg-gray-50"
          )}
          onClick={() => setPosFilter("")}
        >
          All
        </button>
        {positions.map((pos) => (
          <button
            key={pos}
            className={cn(
              "px-2 py-1 text-xs rounded-md border",
              posFilter === pos ? "bg-gray-900 text-white border-gray-900" : "bg-white text-gray-600 border-gray-300 hover:bg-gray-50"
            )}
            onClick={() => setPosFilter(posFilter === pos ? "" : pos)}
          >
            {pos}
          </button>
        ))}
      </div>

      <div className="overflow-x-auto border rounded-lg">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase w-8">#</th>
              <SortHeader label="Player" colKey="full_name" />
              <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Pos</th>
              <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Team</th>
              <SortHeader label="Age" colKey="age" />
              <SortHeader label="AI Value" colKey="ai_value_score" />
              <SortHeader label="Auction $" colKey="auction_value" />
              <SortHeader label="Surplus" colKey="surplus_value" />
              <SortHeader label="Dynasty" colKey="dynasty_value" />
              {showSleeper && <SortHeader label="Sleeper" colKey="sleeper_score" />}
              {showBust && <SortHeader label="Bust" colKey="bust_score" />}
              <SortHeader label="Consistency" colKey="consistency_score" />
              <SortHeader label="Improvement" colKey="improvement_score" />
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {sorted.map((player, i) => (
              <tr key={player.player_id} className="hover:bg-gray-50 transition-colors">
                <td className="px-3 py-2 text-xs text-gray-400">{i + 1}</td>
                <td className="px-3 py-2">
                  <Link
                    href={`/players/${player.player_id}`}
                    className="text-sm font-medium text-blue-600 hover:text-blue-800 hover:underline"
                  >
                    {player.full_name}
                  </Link>
                </td>
                <td className="px-3 py-2 text-xs text-gray-600">{player.position ?? "—"}</td>
                <td className="px-3 py-2 text-xs text-gray-600">{player.team ?? "—"}</td>
                <td className="px-3 py-2 text-xs text-gray-600">{player.age ?? "—"}</td>
                <td className={cn("px-3 py-2 text-sm font-mono font-semibold", scoreColor(player.ai_value_score))}>
                  {formatScore(player.ai_value_score)}
                </td>
                <td className="px-3 py-2 text-sm font-mono">{formatDollar(player.auction_value)}</td>
                <td className={cn("px-3 py-2 text-sm font-mono", surplusColor(player.surplus_value))}>
                  {player.surplus_value != null ? `${player.surplus_value > 0 ? "+" : ""}${formatDollar(player.surplus_value)}` : "—"}
                </td>
                <td className={cn("px-3 py-2 text-sm font-mono", scoreColor(player.dynasty_value))}>
                  {formatScore(player.dynasty_value)}
                </td>
                {showSleeper && (
                  <td className={cn("px-3 py-2 text-sm font-mono", scoreColor(player.sleeper_score))}>
                    {formatScore(player.sleeper_score)}
                  </td>
                )}
                {showBust && (
                  <td className={cn("px-3 py-2 text-sm font-mono", scoreColor(player.bust_score))}>
                    {formatScore(player.bust_score)}
                  </td>
                )}
                <td className={cn("px-3 py-2 text-sm font-mono", scoreColor(player.consistency_score))}>
                  {formatScore(player.consistency_score)}
                </td>
                <td className={cn("px-3 py-2 text-sm font-mono", player.improvement_score != null && player.improvement_score > 0 ? "text-green-600" : player.improvement_score != null && player.improvement_score < -10 ? "text-red-500" : "text-gray-600")}>
                  {player.improvement_score != null ? `${player.improvement_score > 0 ? "+" : ""}${formatScore(player.improvement_score)}` : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {sorted.length === 0 && (
          <div className="text-center py-8 text-gray-400 text-sm">
            No players found
          </div>
        )}
      </div>
    </div>
  );
}
