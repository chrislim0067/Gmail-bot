import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

interface EmptyStateProps {
  icon: LucideIcon;
  title: string;
  description: string;
  action?: React.ReactNode;
  className?: string;
  compact?: boolean;
}

export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
  className,
  compact = false,
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center text-center",
        compact ? "px-4 py-8" : "px-6 py-14",
        className
      )}
    >
      <div
        className={cn(
          "flex items-center justify-center rounded-2xl bg-gradient-to-br from-violet-50 to-pink-50 ring-1 ring-violet-100/80",
          compact ? "h-11 w-11" : "h-14 w-14"
        )}
      >
        <Icon
          className={cn("text-brand", compact ? "h-5 w-5" : "h-6 w-6")}
          strokeWidth={1.75}
        />
      </div>
      <h3 className="mt-4 text-sm font-semibold text-foreground">{title}</h3>
      <p className="mt-1.5 max-w-sm text-sm leading-relaxed text-muted-foreground">
        {description}
      </p>
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}
