"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import type { BattingSeason, PitchingSeason } from "@/lib/types";

interface StatTrendChartProps {
  battingSeasons?: BattingSeason[];
  pitchingSeasons?: PitchingSeason[];
}

export function StatTrendChart({ battingSeasons, pitchingSeasons }: StatTrendChartProps) {
  if (battingSeasons && battingSeasons.length > 0) {
    return <BattingTrends seasons={battingSeasons} />;
  }
  if (pitchingSeasons && pitchingSeasons.length > 0) {
    return <PitchingTrends seasons={pitchingSeasons} />;
  }
  return null;
}

function BattingTrends({ seasons }: { seasons: BattingSeason[] }) {
  const data = [...seasons]
    .sort((a, b) => a.season - b.season)
    .map((s) => ({
      season: s.season,
      wOBA: s.woba,
      xwOBA: s.xwoba,
      "Barrel%": s.barrel_pct != null ? +(s.barrel_pct * 100).toFixed(1) : null,
      "K%": s.k_pct != null ? +(s.k_pct * 100).toFixed(1) : null,
    }));

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-5">
      <h3 className="font-semibold text-gray-900 mb-4">Stat Trends</h3>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div>
          <p className="text-xs text-gray-500 mb-2 font-medium">wOBA vs xwOBA</p>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={data}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="season" tick={{ fontSize: 12 }} />
              <YAxis domain={["auto", "auto"]} tick={{ fontSize: 12 }} />
              <Tooltip />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Line type="monotone" dataKey="wOBA" stroke="#3b82f6" strokeWidth={2} dot={{ r: 4 }} />
              <Line type="monotone" dataKey="xwOBA" stroke="#94a3b8" strokeWidth={2} strokeDasharray="5 5" dot={{ r: 4 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
        <div>
          <p className="text-xs text-gray-500 mb-2 font-medium">Barrel% & K%</p>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={data}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="season" tick={{ fontSize: 12 }} />
              <YAxis tick={{ fontSize: 12 }} />
              <Tooltip />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Line type="monotone" dataKey="Barrel%" stroke="#22c55e" strokeWidth={2} dot={{ r: 4 }} />
              <Line type="monotone" dataKey="K%" stroke="#ef4444" strokeWidth={2} dot={{ r: 4 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}

function PitchingTrends({ seasons }: { seasons: PitchingSeason[] }) {
  const data = [...seasons]
    .sort((a, b) => a.season - b.season)
    .map((s) => ({
      season: s.season,
      ERA: s.era,
      FIP: s.fip,
      "K%": s.k_pct != null ? +(s.k_pct * 100).toFixed(1) : null,
      "BB%": s.bb_pct != null ? +(s.bb_pct * 100).toFixed(1) : null,
    }));

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-5">
      <h3 className="font-semibold text-gray-900 mb-4">Stat Trends</h3>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div>
          <p className="text-xs text-gray-500 mb-2 font-medium">ERA vs FIP</p>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={data}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="season" tick={{ fontSize: 12 }} />
              <YAxis domain={["auto", "auto"]} tick={{ fontSize: 12 }} />
              <Tooltip />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Line type="monotone" dataKey="ERA" stroke="#ef4444" strokeWidth={2} dot={{ r: 4 }} />
              <Line type="monotone" dataKey="FIP" stroke="#94a3b8" strokeWidth={2} strokeDasharray="5 5" dot={{ r: 4 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
        <div>
          <p className="text-xs text-gray-500 mb-2 font-medium">K% & BB%</p>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={data}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="season" tick={{ fontSize: 12 }} />
              <YAxis tick={{ fontSize: 12 }} />
              <Tooltip />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Line type="monotone" dataKey="K%" stroke="#22c55e" strokeWidth={2} dot={{ r: 4 }} />
              <Line type="monotone" dataKey="BB%" stroke="#f59e0b" strokeWidth={2} dot={{ r: 4 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
