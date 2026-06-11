import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatPercent(value: number | null | undefined): string {
  if (value == null) return "—";
  return `${(value * 100).toFixed(1)}%`;
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return "—";
  return new Date(value).toLocaleString();
}

const DATE_PART_OPTS: Intl.DateTimeFormatOptions = {
  month: "short",
  day: "numeric",
  year: "numeric",
};

const TIME_PART_OPTS: Intl.DateTimeFormatOptions = {
  hour: "numeric",
  minute: "2-digit",
};

export function formatDateParts(
  value: string | null | undefined
): { date: string; time: string } | null {
  if (!value) return null;
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return null;
  return {
    date: parsed.toLocaleDateString(undefined, DATE_PART_OPTS),
    time: parsed.toLocaleTimeString(undefined, TIME_PART_OPTS),
  };
}

export function formatSendDelay(
  plannedAt: string | null | undefined,
  sentAt: string | null | undefined
): string | null {
  if (!plannedAt || !sentAt) return null;
  const diffSec = Math.round(
    (new Date(sentAt).getTime() - new Date(plannedAt).getTime()) / 1000
  );
  if (diffSec < 0) return null;
  if (diffSec < 60) return `${diffSec}s after planned`;
  const mins = Math.floor(diffSec / 60);
  const secs = diffSec % 60;
  return secs > 0 ? `${mins}m ${secs}s after planned` : `${mins}m after planned`;
}

export function formatNumber(value: number | null | undefined): string {
  if (value == null) return "—";
  return value.toLocaleString();
}

export function formatCountdown(totalSeconds: number): string {
  if (totalSeconds <= 0) return "Available now";
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
  if (hours > 0) {
    return `${hours}h ${minutes}m ${seconds.toString().padStart(2, "0")}s`;
  }
  return `${minutes}m ${seconds.toString().padStart(2, "0")}s`;
}
