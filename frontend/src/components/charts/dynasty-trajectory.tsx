"use client";

import { useEffect, useState } from "react";
import {
  AreaChart,
  Area,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";
import { getPlayerTrajectory } from "@/lib/api";

interface TrajectoryPoint {
  season: number;
  projected_value: number;
  upper_bound: number;
  lower_bound: number;
  age: number;
}

interface TrajectoryData {
  player_id: number;
  current_value: number;
  peak_season: number;
  peak_value: number;
  career_value_remaining: number;
  trajectory_grade: string;
  trajectory: TrajectoryPoint[];
}

interface DynastyTrajectoryChartProps {
  playerId: number;
  playerName?: string;
}

const GRADE_COLORS: Record<string, string> = {
  Rising: "text-green-600 bg-green-50 border-green-200",
  Peak: "text-blue-600 bg-blue-50 border-blue-200",
  Plateau: "text-amber-600 bg-amber-50 border-amber-200",
  Declining: "text-orange-600 bg-orange-50 border-orange-200",
  "Late Career": "text-red-600 bg-red-50 border-red-200",
};

export function DynastyTrajectoryChart({ playerId, playerName }: DynastyTrajectoryChartProps) {
  const [data, setData] = useState<TrajectoryData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    if (!playerId) return;
    setLoading(true);
    getPlayerTrajectory(playerId)
      .then(setData)
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  }, [playerId]);

  if (loading) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-5">
        <div className="animate-pulse">
          <div className="h-5 bg-gray-200 rounded w-1/4 mb-4" />
          <div className="h-48 bg-gray-100 rounded" />
        </div>
      </div>
    );
  }

  if (error || !data) {
    return null; // Silently hide if trajectory isn't available
  }

  const chartData = [
    // Current season as starting point
    {
      season: data.trajectory[0]?.season ? data.trajectory[0].season - 1 : 2025,
      projected_value: data.current_value,
      upper_bound: data.current_value,
      lower_bound: data.current_value,
      label: "Now",
    },
    ...data.trajectory.map((p) => ({
      season: p.season,
      projected_value: p.projected_value,
      upper_bound: p.upper_bound,
      lower_bound: p.lower_bound,
      label: `${p.season} (age ${p.age})`,
    })),
  ];

  const gradeStyle = GRADE_COLORS[data.trajectory_grade] || "text-gray-600 bg-gray-50 border-gray-200";

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold text-gray-900">Dynasty Trajectory</h3>
        <div className="flex items-center gap-3">
          <span className={`text-xs font-medium px-2 py-1 rounded-full border ${gradeStyle}`}>
            {data.trajectory_grade}
          </span>
          <span className="text-xs text-gray-500">
            Peak: {data.peak_value.toFixed(0)} ({data.peak_season})
          </span>
        </div>
      </div>

      <ResponsiveContainer width="100%" height={250}>
        <AreaChart data={chartData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
          <defs>
            <linearGradient id="confidenceBand" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.15} />
              <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.05} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis
            dataKey="season"
            tick={{ fontSize: 12 }}
            tickFormatter={(v) => String(v)}
          />
          <YAxis
            domain={[0, 100]}
            tick={{ fontSize: 12 }}
            label={{ value: "Value", angle: -90, position: "insideLeft", style: { fontSize: 11 } }}
          />
          <Tooltip
            formatter={(value: number, name: string) => [
              value.toFixed(1),
              name === "projected_value" ? "Projected" :
              name === "upper_bound" ? "Optimistic" :
              name === "lower_bound" ? "Conservative" : name,
            ]}
            labelFormatter={(label) => {
              const point = chartData.find((d) => d.season === label);
              return point?.label || String(label);
            }}
          />
          <Area
            type="monotone"
            dataKey="upper_bound"
            stroke="none"
            fill="url(#confidenceBand)"
            fillOpacity={1}
          />
          <Area
            type="monotone"
            dataKey="lower_bound"
            stroke="none"
            fill="#ffffff"
            fillOpacity={1}
          />
          <Line
            type="monotone"
            dataKey="projected_value"
            stroke="#3b82f6"
            strokeWidth={2.5}
            dot={{ r: 4, fill: "#3b82f6" }}
            name="Projected Value"
          />
          <Line
            type="monotone"
            dataKey="upper_bound"
            stroke="#93c5fd"
            strokeWidth={1}
            strokeDasharray="4 4"
            dot={false}
            name="80% Upper"
          />
          <Line
            type="monotone"
            dataKey="lower_bound"
            stroke="#93c5fd"
            strokeWidth={1}
            strokeDasharray="4 4"
            dot={false}
            name="80% Lower"
          />
        </AreaChart>
      </ResponsiveContainer>

      {/* Summary stats */}
      <div className="grid grid-cols-3 gap-4 mt-4 pt-3 border-t border-gray-100">
        <div>
          <p className="text-xs text-gray-500">Current Value</p>
          <p className="text-sm font-semibold font-mono">{data.current_value.toFixed(1)}</p>
        </div>
        <div>
          <p className="text-xs text-gray-500">Peak Projection</p>
          <p className="text-sm font-semibold font-mono">{data.peak_value.toFixed(1)}</p>
        </div>
        <div>
          <p className="text-xs text-gray-500">Total Remaining</p>
          <p className="text-sm font-semibold font-mono">{data.career_value_remaining.toFixed(0)}</p>
        </div>
      </div>
    </div>
  );
}
