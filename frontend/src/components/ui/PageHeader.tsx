import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

interface PageHeaderProps {
  title: string;
  description?: string;
  actions?: ReactNode;
  badge?: ReactNode;
  className?: string;
}

export function PageHeader({
  title,
  description,
  actions,
  badge,
  className,
}: PageHeaderProps) {
  return (
    <div
      className={cn(
        "mb-2 flex flex-col gap-5 sm:flex-row sm:items-end sm:justify-between",
        className
      )}
    >
      <div className="min-w-0 flex-1 animate-slide-up">
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="font-display text-3xl tracking-tight text-foreground sm:text-[2.125rem]">
            {title}
          </h1>
          {badge}
        </div>
        {description && (
          <p className="mt-2 max-w-2xl text-[15px] leading-relaxed text-muted-foreground">
            {description}
          </p>
        )}
      </div>
      {actions && (
        <div className="flex shrink-0 flex-wrap items-center gap-2.5 pb-0.5">
          {actions}
        </div>
      )}
    </div>
  );
}
