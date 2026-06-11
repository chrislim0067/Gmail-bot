import { cn } from "@/lib/utils";

interface ProgressBarProps {
  value: number;
  max?: number;
  label?: string;
  showValue?: boolean;
  size?: "sm" | "md";
  variant?: "default" | "success" | "warning" | "danger";
  className?: string;
}

const barVariants = {
  default: "bg-gradient-to-r from-violet-500 via-pink-500 to-amber-400",
  success: "bg-emerald-500",
  warning: "bg-amber-500",
  danger: "bg-red-500",
};

export function ProgressBar({
  value,
  max = 100,
  label,
  showValue = false,
  size = "md",
  variant = "default",
  className,
}: ProgressBarProps) {
  const pct = max > 0 ? Math.min(100, Math.round((value / max) * 100)) : 0;

  return (
    <div className={cn("w-full", className)}>
      {(label || showValue) && (
        <div className="mb-2 flex items-center justify-between gap-2 text-xs">
          {label && (
            <span className="font-semibold uppercase tracking-[0.1em] text-muted-foreground">
              {label}
            </span>
          )}
          {showValue && (
            <span className="tabular-nums font-medium text-foreground">{pct}%</span>
          )}
        </div>
      )}
      <div
        className={cn(
          "w-full overflow-hidden rounded-full bg-stone-100/90 ring-1 ring-stone-200/50",
          size === "sm" ? "h-1.5" : "h-2"
        )}
      >
        <div
          className={cn(
            "h-full rounded-full transition-all duration-500 ease-out",
            barVariants[variant]
          )}
          style={{ width: `${pct}%` }}
          role="progressbar"
          aria-valuenow={value}
          aria-valuemin={0}
          aria-valuemax={max}
        />
      </div>
    </div>
  );
}
