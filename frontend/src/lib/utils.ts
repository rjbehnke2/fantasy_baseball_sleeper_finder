import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatStat(value: number | null | undefined, decimals = 3): string {
  if (value == null) return "—";
  if (Math.abs(value) >= 10) return value.toFixed(1);
  return value.toFixed(decimals);
}

export function formatPct(value: number | null | undefined): string {
  if (value == null) return "—";
  return `${(value * 100).toFixed(1)}%`;
}

export function formatDollar(value: number | null | undefined): string {
  if (value == null) return "—";
  return `$${value.toFixed(0)}`;
}

export function formatScore(value: number | null | undefined): string {
  if (value == null) return "—";
  return value.toFixed(1);
}

export function scoreColor(score: number | null | undefined): string {
  if (score == null) return "text-gray-400";
  if (score >= 80) return "text-green-600";
  if (score >= 60) return "text-green-500";
  if (score >= 40) return "text-yellow-500";
  if (score >= 20) return "text-orange-500";
  return "text-red-500";
}

export function scoreBg(score: number | null | undefined): string {
  if (score == null) return "bg-gray-100";
  if (score >= 80) return "bg-green-100";
  if (score >= 60) return "bg-green-50";
  if (score >= 40) return "bg-yellow-50";
  if (score >= 20) return "bg-orange-50";
  return "bg-red-50";
}

export function surplusColor(surplus: number | null | undefined): string {
  if (surplus == null) return "text-gray-400";
  if (surplus > 5) return "text-green-600 font-semibold";
  if (surplus > 0) return "text-green-500";
  if (surplus > -5) return "text-orange-500";
  return "text-red-500 font-semibold";
}
