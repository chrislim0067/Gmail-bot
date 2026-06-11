import type { LucideIcon } from "lucide-react";
import { AlertCircle, CheckCircle2, Info, X } from "lucide-react";
import { cn } from "@/lib/utils";

type AlertVariant = "info" | "success" | "warning" | "danger";

interface AlertProps {
  variant?: AlertVariant;
  title?: string;
  children: React.ReactNode;
  onDismiss?: () => void;
  className?: string;
  icon?: LucideIcon;
}

const variants: Record<
  AlertVariant,
  { container: string; icon: LucideIcon; iconClass: string }
> = {
  info: {
    container: "border-violet-200/80 bg-violet-50/90 text-violet-950",
    icon: Info,
    iconClass: "text-violet-600",
  },
  success: {
    container: "border-emerald-200/80 bg-emerald-50/90 text-emerald-950",
    icon: CheckCircle2,
    iconClass: "text-emerald-600",
  },
  warning: {
    container: "border-amber-200/80 bg-amber-50/90 text-amber-950",
    icon: AlertCircle,
    iconClass: "text-amber-600",
  },
  danger: {
    container: "border-red-200/80 bg-red-50/90 text-red-950",
    icon: AlertCircle,
    iconClass: "text-red-600",
  },
};

export function Alert({
  variant = "info",
  title,
  children,
  onDismiss,
  className,
  icon,
}: AlertProps) {
  const config = variants[variant];
  const Icon = icon ?? config.icon;

  return (
    <div
      className={cn(
        "flex gap-3 rounded-2xl border px-4 py-3.5 text-sm shadow-soft animate-fade-in backdrop-blur-sm",
        config.container,
        className
      )}
      role="alert"
    >
      <Icon className={cn("mt-0.5 h-4 w-4 shrink-0", config.iconClass)} />
      <div className="min-w-0 flex-1">
        {title && <p className="font-semibold">{title}</p>}
        <div className={cn(title && "mt-0.5", "leading-relaxed")}>{children}</div>
      </div>
      {onDismiss && (
        <button
          type="button"
          onClick={onDismiss}
          className="shrink-0 rounded-lg p-1 opacity-60 transition-opacity hover:bg-black/5 hover:opacity-100"
          aria-label="Dismiss"
        >
          <X className="h-4 w-4" />
        </button>
      )}
    </div>
  );
}
