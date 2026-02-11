"use client";

import { useEffect, useState } from "react";
import { getScoutingReport } from "@/lib/api";
import type { ScoutingReport } from "@/lib/types";

interface ScoutingReportDisplayProps {
  playerId: number;
  reportType?: string;
}

export function ScoutingReportDisplay({
  playerId,
  reportType = "full",
}: ScoutingReportDisplayProps) {
  const [report, setReport] = useState<ScoutingReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    getScoutingReport(playerId, reportType)
      .then((data) => {
        if (!cancelled) setReport(data);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [playerId, reportType]);

  if (loading) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <div className="animate-pulse space-y-3">
          <div className="h-4 bg-gray-200 rounded w-3/4" />
          <div className="h-3 bg-gray-200 rounded w-full" />
          <div className="h-3 bg-gray-200 rounded w-5/6" />
          <div className="h-3 bg-gray-200 rounded w-full" />
        </div>
        <p className="text-sm text-gray-400 mt-4">Loading scouting report...</p>
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className="bg-gray-50 rounded-lg border border-gray-200 p-6 text-center">
        <p className="text-gray-500 text-sm">
          No scouting report available yet.
        </p>
        <p className="text-gray-400 text-xs mt-1">
          Reports are generated in batch for top players.
        </p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
      <div className="px-6 py-4 bg-gradient-to-r from-blue-50 to-indigo-50 border-b border-gray-200 flex items-center justify-between">
        <div>
          <h3 className="font-semibold text-gray-900">AI Scouting Report</h3>
          <p className="text-xs text-gray-500 mt-0.5">
            Generated {new Date(report.generated_at).toLocaleDateString()}
            {report.stale && (
              <span className="ml-2 text-amber-600 font-medium">
                (may be outdated)
              </span>
            )}
          </p>
        </div>
        <span className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded-full font-medium">
          AI Generated
        </span>
      </div>
      <div className="px-6 py-4 prose prose-sm max-w-none">
        {report.content.split("\n").map((line, i) => {
          if (line.startsWith("## ")) {
            return (
              <h4 key={i} className="text-base font-semibold text-gray-900 mt-4 mb-2">
                {line.replace("## ", "")}
              </h4>
            );
          }
          if (line.trim() === "") return <br key={i} />;
          return (
            <p key={i} className="text-gray-700 leading-relaxed mb-2">
              {line}
            </p>
          );
        })}
      </div>
    </div>
  );
}
