import { cn } from "@/lib/utils";
import type { AccountTier, CampaignStatus, RiskLevel } from "@/types/api";

type BadgeVariant =
  | "default"
  | "success"
  | "warning"
  | "danger"
  | "info"
  | "muted";

const variantStyles: Record<BadgeVariant, string> = {
  default: "bg-stone-100/90 text-stone-700 ring-1 ring-stone-200/80",
  success: "bg-emerald-50 text-emerald-800 ring-1 ring-emerald-200/70",
  warning: "bg-amber-50 text-amber-900 ring-1 ring-amber-200/70",
  danger: "bg-red-50 text-red-800 ring-1 ring-red-200/70",
  info: "bg-violet-50 text-violet-800 ring-1 ring-violet-200/70",
  muted: "bg-stone-50 text-stone-500 ring-1 ring-stone-200/60",
};

interface BadgeProps {
  children: React.ReactNode;
  variant?: BadgeVariant;
  className?: string;
  dot?: boolean;
}

export function Badge({
  children,
  variant = "default",
  className,
  dot = false,
}: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-[0.12em]",
        variantStyles[variant],
        className
      )}
    >
      {dot && (
        <span
          className={cn(
            "h-1.5 w-1.5 rounded-full",
            variant === "success" && "bg-emerald-500",
            variant === "warning" && "bg-amber-500",
            variant === "danger" && "bg-red-500",
            variant === "info" && "bg-violet-500",
            (variant === "default" || variant === "muted") && "bg-stone-400"
          )}
        />
      )}
      {children}
    </span>
  );
}

const tierVariants: Record<AccountTier, BadgeVariant> = {
  new: "info",
  warming: "warning",
  stable: "success",
  trusted: "success",
  restricted: "danger",
  paused: "muted",
};

export function TierBadge({ tier }: { tier: AccountTier }) {
  return <Badge variant={tierVariants[tier]}>{tier}</Badge>;
}

const riskVariants: Record<RiskLevel, BadgeVariant> = {
  low: "success",
  medium: "warning",
  high: "danger",
};

export function RiskBadge({ level }: { level: RiskLevel }) {
  return (
    <Badge variant={riskVariants[level]} dot>
      {level} risk
    </Badge>
  );
}

const campaignVariants: Record<CampaignStatus, BadgeVariant> = {
  draft: "muted",
  scheduled: "info",
  running: "success",
  paused: "warning",
  completed: "default",
  cancelled: "danger",
};

const campaignLabels: Record<CampaignStatus, string> = {
  draft: "Draft",
  scheduled: "Scheduled",
  running: "Running",
  paused: "Paused",
  completed: "Completed",
  cancelled: "Cancelled",
};

export function StatusBadge({ status }: { status: CampaignStatus }) {
  return (
    <Badge variant={campaignVariants[status]} dot={status === "running"}>
      {campaignLabels[status]}
    </Badge>
  );
}

type SendQueueStatus = "up_next" | "ready" | "in_line" | "resting" | "paused";

const sendStatusConfig: Record<
  SendQueueStatus,
  { variant: BadgeVariant; label: string }
> = {
  up_next: { variant: "success", label: "Up next" },
  ready: { variant: "success", label: "Ready" },
  in_line: { variant: "info", label: "In line" },
  resting: { variant: "warning", label: "Resting" },
  paused: { variant: "muted", label: "Paused" },
};

export function SendStatusBadge({ status }: { status: SendQueueStatus }) {
  const config = sendStatusConfig[status];
  return (
    <Badge variant={config.variant} dot>
      {config.label}
    </Badge>
  );
}

export function HealthBadge({ score }: { score: number }) {
  const variant: BadgeVariant =
    score >= 70 ? "success" : score >= 40 ? "warning" : "danger";
  const label = score >= 70 ? "Healthy" : score >= 40 ? "Fair" : "At risk";
  return (
    <Badge variant={variant} dot>
      {label}
    </Badge>
  );
}

export function ActiveBadge({ active }: { active: boolean }) {
  return (
    <Badge variant={active ? "success" : "muted"} dot={active}>
      {active ? "Active" : "Inactive"}
    </Badge>
  );
}
