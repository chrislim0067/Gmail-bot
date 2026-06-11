import { cn } from "@/lib/utils";
import type { LucideIcon } from "lucide-react";

interface StatCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon?: LucideIcon;
  trend?: "up" | "down" | "neutral";
  className?: string;
}

export function StatCard({
  title,
  value,
  subtitle,
  icon: Icon,
  trend,
  className,
}: StatCardProps) {
  return (
    <div
      className={cn(
        "group relative overflow-hidden rounded-2xl border border-border-subtle bg-white/90 p-6 shadow-soft transition-all duration-300",
        "hover:-translate-y-0.5 hover:border-violet-100 hover:shadow-float",
        className
      )}
    >
      <div className="stat-accent-bar opacity-80 transition-opacity group-hover:opacity-100" />
      <div className="flex items-start justify-between gap-4 pt-1">
        <div className="min-w-0">
          <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">
            {title}
          </p>
          <p className="font-display mt-3 text-4xl tracking-tight text-foreground tabular-nums">
            {value}
          </p>
          {subtitle && (
            <p
              className={cn(
                "mt-2 text-xs leading-relaxed",
                trend === "up" && "text-success",
                trend === "down" && "text-danger",
                (!trend || trend === "neutral") && "text-muted-foreground"
              )}
            >
              {subtitle}
            </p>
          )}
        </div>
        {Icon && (
          <div className="rounded-2xl bg-gradient-to-br from-violet-50 to-pink-50 p-3 ring-1 ring-violet-100/80 transition-transform group-hover:scale-105">
            <Icon className="h-5 w-5 text-brand" strokeWidth={1.75} />
          </div>
        )}
      </div>
    </div>
  );
}

export const MetricCard = StatCard;
