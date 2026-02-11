"use client";

import { cn, formatDollar, surplusColor } from "@/lib/utils";

interface DollarBadgeProps {
  value: number | null | undefined;
  surplus?: number | null;
  size?: "sm" | "md" | "lg";
}

export function DollarBadge({ value, surplus, size = "md" }: DollarBadgeProps) {
  const sizeClasses = {
    sm: "text-xs",
    md: "text-sm",
    lg: "text-lg font-bold",
  };

  return (
    <div className="inline-flex items-center gap-2">
      <span className={cn("font-mono text-gray-900", sizeClasses[size])}>
        {formatDollar(value)}
      </span>
      {surplus != null && (
        <span className={cn("text-xs font-mono", surplusColor(surplus))}>
          ({surplus > 0 ? "+" : ""}{formatDollar(surplus)})
        </span>
      )}
    </div>
  );
}
