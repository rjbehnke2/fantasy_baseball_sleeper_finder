"use client";

import { cn, scoreColor, scoreBg, formatScore } from "@/lib/utils";

interface ScoreBadgeProps {
  label: string;
  score: number | null | undefined;
  size?: "sm" | "md" | "lg";
  showLabel?: boolean;
}

export function ScoreBadge({ label, score, size = "md", showLabel = true }: ScoreBadgeProps) {
  const sizeClasses = {
    sm: "text-xs px-1.5 py-0.5",
    md: "text-sm px-2 py-1",
    lg: "text-base px-3 py-1.5 font-semibold",
  };

  return (
    <div className={cn("inline-flex items-center gap-1.5 rounded-md", scoreBg(score), sizeClasses[size])}>
      {showLabel && <span className="text-gray-500 text-xs">{label}</span>}
      <span className={cn("font-mono", scoreColor(score))}>{formatScore(score)}</span>
    </div>
  );
}
