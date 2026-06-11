"use client";

import { useEffect, useMemo, useState } from "react";
import { Clock, Mail } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import { formatCountdown, formatDate } from "@/lib/utils";
import { queueApi } from "@/lib/api";
import { LIVE_POLL_MS, UI_TICK_MS } from "@/lib/polling";
import type { AccountSendTimeline, AccountSendTimelineEntry } from "@/types/api";

function remainingSeconds(availableAt: string | null | undefined, nowMs: number): number {
  if (!availableAt) return 0;
  return Math.max(0, Math.ceil((new Date(availableAt).getTime() - nowMs) / 1000));
}

type SimpleAccountView = {
  badge: string;
  badgeVariant: "success" | "info" | "warning" | "muted";
  headline: string;
  nextSendLabel: string;
  nextSendValue: string;
  sentTodayLabel: string;
};

function getSimpleAccountView(
  account: AccountSendTimelineEntry,
  remaining: number,
  cooldownMinutes: number
): SimpleAccountView {
  const sentToday = `${account.sent_today} email${account.sent_today === 1 ? "" : "s"} sent today`;

  if (account.reason === "next_to_send") {
    return {
      badge: "Up next",
      badgeVariant: "success",
      headline: "This account will send the next email soon.",
      nextSendLabel: "Next send",
      nextSendValue: "Very soon",
      sentTodayLabel: sentToday,
    };
  }

  if (account.available_now) {
    return {
      badge: "Ready",
      badgeVariant: "success",
      headline: "This account is ready to send.",
      nextSendLabel: "Next send",
      nextSendValue: "Any moment",
      sentTodayLabel: sentToday,
    };
  }

  if (account.reason === "waiting_turn") {
    const turn =
      account.queue_position != null ? ` (${account.queue_position}${ordinal(account.queue_position)} in line)` : "";
    return {
      badge: "In line",
      badgeVariant: "info",
      headline: `Waiting for the account ahead to finish${turn}.`,
      nextSendLabel: "Expected",
      nextSendValue: "After the previous account sends",
      sentTodayLabel: sentToday,
    };
  }

  if (account.reason === "pool_stagger") {
    return {
      badge: remaining > 0 ? formatCountdown(remaining) : "Short wait",
      badgeVariant: "info",
      headline: "Pausing briefly before the next account sends.",
      nextSendLabel: "Ready at",
      nextSendValue: account.available_at ? formatDate(account.available_at) : "Soon",
      sentTodayLabel: sentToday,
    };
  }

  if (account.reason === "daily_cap") {
    return {
      badge: "Daily limit",
      badgeVariant: "warning",
      headline: "This account reached its daily email limit.",
      nextSendLabel: "Can send again",
      nextSendValue: account.available_at ? formatDate(account.available_at) : "Tomorrow",
      sentTodayLabel: sentToday,
    };
  }

  if (
    account.reason === "hourly_cap" ||
    account.reason === "inter_send_delay" ||
    remaining > 0
  ) {
    return {
      badge: remaining > 0 ? formatCountdown(remaining) : "Resting",
      badgeVariant: "warning",
      headline: `Resting after a recent send (${cooldownMinutes} min wait between emails from the same account).`,
      nextSendLabel: "Can send again at",
      nextSendValue: account.available_at ? formatDate(account.available_at) : "—",
      sentTodayLabel: sentToday,
    };
  }

  if (account.reason === "account_blocked" || account.reason === "account_inactive") {
    return {
      badge: "Paused",
      badgeVariant: "muted",
      headline: "This account is paused and will not send until you turn it back on.",
      nextSendLabel: "Status",
      nextSendValue: "Not sending",
      sentTodayLabel: sentToday,
    };
  }

  return {
    badge: "Unavailable",
    badgeVariant: "muted",
    headline: "This account cannot send right now.",
    nextSendLabel: "Check again",
    nextSendValue: account.available_at ? formatDate(account.available_at) : "Later",
    sentTodayLabel: sentToday,
  };
}

function ordinal(n: number): string {
  if (n === 1) return "st";
  if (n === 2) return "nd";
  if (n === 3) return "rd";
  return "th";
}

interface SendTimelineProps {
  timeline: AccountSendTimeline | null;
  loading?: boolean;
  compact?: boolean;
}

export function SendTimeline({ timeline, loading, compact }: SendTimelineProps) {
  const [nowMs, setNowMs] = useState(() => Date.now());

  useEffect(() => {
    const timer = setInterval(() => setNowMs(Date.now()), UI_TICK_MS);
    return () => clearInterval(timer);
  }, []);

  const cooldownMinutes = Math.round(
    (timeline?.account_cooldown_seconds ??
      timeline?.inter_send_delay_seconds ??
      1800) / 60
  );
  const gapMin = Math.round((timeline?.inter_account_delay_min_seconds ?? 120) / 60);
  const gapMax = Math.round((timeline?.inter_account_delay_max_seconds ?? 180) / 60);
  const gapLabel = gapMin === gapMax ? `${gapMin} min` : `${gapMin}–${gapMax} min`;

  const rows = useMemo(() => {
    if (!timeline) return [];
    return timeline.accounts.map((account) => {
      const remaining = account.available_now
        ? 0
        : remainingSeconds(account.available_at, nowMs);
      return {
        account,
        view: getSimpleAccountView(account, remaining, cooldownMinutes),
      };
    });
  }, [timeline, nowMs, cooldownMinutes]);

  return (
    <Card>
      <CardHeader className={compact ? "pb-2" : undefined}>
        <CardTitle className="flex items-center gap-2 text-base">
          <Clock className="h-4 w-4 text-brand" />
          Your sending accounts
        </CardTitle>
        {!compact && (
          <p className="text-sm text-muted-foreground">
            Emails go out one account at a time, in order. Each account waits{" "}
            {cooldownMinutes} minutes before it can send again, with about {gapLabel}{" "}
            between different accounts.
          </p>
        )}
      </CardHeader>
      <CardContent className="space-y-3">
        {loading ? (
          <div className="flex h-24 items-center justify-center">
            <LoadingSpinner size="sm" />
          </div>
        ) : rows.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No Gmail accounts connected yet. Connect an account under Gmail Accounts.
          </p>
        ) : (
          rows.map(({ account, view }) => (
            <div
              key={account.gmail_account_id}
              className="rounded-2xl border border-border-subtle bg-white/80 p-4 shadow-soft transition-all duration-300 hover:-translate-y-0.5 hover:border-violet-100 hover:shadow-float"
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="flex min-w-0 items-start gap-3">
                  <div className="mt-0.5 rounded-xl bg-gradient-to-br from-violet-50 to-pink-50 p-2.5 ring-1 ring-violet-100/80">
                    <Mail className="h-4 w-4 text-brand" />
                  </div>
                  <div className="min-w-0">
                    <p className="truncate font-medium text-foreground">{account.email}</p>
                    <p className="mt-1 text-sm text-muted-foreground">{view.headline}</p>
                  </div>
                </div>
                <Badge variant={view.badgeVariant}>{view.badge}</Badge>
              </div>

              <div className="mt-3 grid gap-2 border-t border-border-subtle pt-3 text-sm sm:grid-cols-3">
                <div>
                  <p className="text-[10px] font-semibold uppercase tracking-[0.12em] text-muted-foreground">
                    Last email sent
                  </p>
                  <p className="mt-0.5 text-foreground">
                    {account.last_send_at ? formatDate(account.last_send_at) : "Not yet"}
                  </p>
                </div>
                <div>
                  <p className="text-[10px] font-semibold uppercase tracking-[0.12em] text-muted-foreground">
                    {view.nextSendLabel}
                  </p>
                  <p className="mt-0.5 font-medium text-foreground">{view.nextSendValue}</p>
                </div>
                <div>
                  <p className="text-[10px] font-semibold uppercase tracking-[0.12em] text-muted-foreground">
                    Today
                  </p>
                  <p className="mt-0.5 text-foreground">{view.sentTodayLabel}</p>
                </div>
              </div>
            </div>
          ))
        )}
      </CardContent>
    </Card>
  );
}

export function useAccountSendTimeline(
  pollMs = LIVE_POLL_MS,
  refreshKey = 0,
  enabled = true
) {
  const [timeline, setTimeline] = useState<AccountSendTimeline | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!enabled) {
      setLoading(false);
      return;
    }

    let cancelled = false;
    let requestSeq = 0;
    let pollInFlight = false;

    async function load(options?: { silent?: boolean }) {
      if (options?.silent && pollInFlight) return;
      const seq = ++requestSeq;
      if (options?.silent) pollInFlight = true;
      else setLoading(true);

      try {
        const data = await queueApi.accountTimeline();
        if (cancelled || seq !== requestSeq) return;
        setTimeline(data);
      } catch {
        if (cancelled || seq !== requestSeq) return;
        setTimeline(null);
      } finally {
        if (options?.silent) pollInFlight = false;
        if (!cancelled && seq === requestSeq) setLoading(false);
      }
    }

    void load();
    if (pollMs <= 0) {
      return () => {
        cancelled = true;
        requestSeq += 1;
      };
    }
    const interval = setInterval(() => {
      void load({ silent: true });
    }, pollMs);
    return () => {
      cancelled = true;
      requestSeq += 1;
      clearInterval(interval);
    };
  }, [pollMs, refreshKey, enabled]);

  return { timeline, loading };
}
