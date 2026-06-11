"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  Activity,
  ArrowRight,
  Mail,
  Megaphone,
  MessageSquare,
  TrendingUp,
} from "lucide-react";
import { Alert } from "@/components/ui/Alert";
import { HealthBadge, StatusBadge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { PageLoader } from "@/components/ui/LoadingSpinner";
import { StatCard } from "@/components/ui/StatCard";
import { useIntervalPoll } from "@/hooks/useIntervalPoll";
import {
  analyticsApi,
  campaignsApi,
  healthApi,
  riskApi,
} from "@/lib/api";
import { campaignEmailsSent, campaignReplies } from "@/lib/campaign-display";
import { BACKEND_POLL_MS } from "@/lib/polling";
import { formatNumber, formatPercent } from "@/lib/utils";
import type { Campaign, HealthAccount, RiskOverview } from "@/types/api";

export default function DashboardPage() {
  const [analytics, setAnalytics] = useState({
    sent: 0,
    replied: 0,
    bounced: 0,
    unsubscribed: 0,
    reply_rate: 0,
    bounce_rate: 0,
  });
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [healthAccounts, setHealthAccounts] = useState<HealthAccount[]>([]);
  const [risk, setRisk] = useState<RiskOverview | null>(null);
  const [loading, setLoading] = useState(true);

  const loadDashboard = useCallback(async (options?: { silent?: boolean }) => {
    if (!options?.silent) setLoading(true);
    try {
      const [overview, runningCampaigns, health, riskOverview] = await Promise.all([
        analyticsApi.overview().catch(() => null),
        campaignsApi.list({ status: "running", limit: 5 }).catch(() => ({
          items: [],
          total: 0,
          page: 1,
          limit: 5,
        })),
        healthApi.accounts().catch(() => ({ items: [] })),
        riskApi.overview().catch(() => null),
      ]);
      if (overview) setAnalytics(overview);
      setCampaigns(runningCampaigns?.items ?? []);
      setHealthAccounts(health?.items ?? []);
      setRisk(riskOverview);
    } finally {
      if (!options?.silent) setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadDashboard();
  }, [loadDashboard]);

  useIntervalPoll(loadDashboard, BACKEND_POLL_MS, campaigns.length > 0);

  const pausedAccounts = healthAccounts.filter(
    (a) => a.status === "paused" || a.status === "auth_error"
  ).length;

  if (loading) return <PageLoader />;

  return (
    <div className="space-y-8">
      <div className="relative overflow-hidden rounded-3xl border border-white/60 bg-gradient-to-br from-violet-600 via-pink-600 to-amber-500 p-8 shadow-float sm:p-10">
        <div className="pointer-events-none absolute -right-16 -top-16 h-48 w-48 rounded-full bg-white/10 blur-2xl" />
        <div className="pointer-events-none absolute -bottom-12 -left-8 h-40 w-40 rounded-full bg-amber-300/20 blur-2xl" />
        <div className="relative">
          <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-white/60">
            Overview
          </p>
          <h1 className="font-display mt-2 text-3xl tracking-tight text-white sm:text-4xl">
            Your outreach at a glance
          </h1>
          <p className="mt-3 max-w-xl text-sm leading-relaxed text-white/75">
            Monitor performance, active campaigns, and account health — all in one place.
          </p>
        </div>
      </div>

      {risk?.review_required && (
        <Alert variant="warning" title="Action required">
          Sending is paused until you review a risk alert.{" "}
          <Link href="/risk" className="font-medium underline underline-offset-2">
            Review risk budget
          </Link>
        </Alert>
      )}

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard
          title="Emails sent"
          value={formatNumber(analytics.sent)}
          subtitle={`${formatNumber(analytics.replied)} replies received`}
          icon={Mail}
        />
        <StatCard
          title="Reply rate"
          value={formatPercent(analytics.reply_rate)}
          subtitle="Engagement from recipients"
          icon={MessageSquare}
          trend="up"
        />
        <StatCard
          title="Bounce rate"
          value={formatPercent(analytics.bounce_rate)}
          subtitle={`${formatNumber(analytics.bounced)} invalid addresses`}
          icon={TrendingUp}
          trend={analytics.bounce_rate > 0.05 ? "down" : "neutral"}
        />
        <StatCard
          title="Active campaigns"
          value={campaigns.length}
          subtitle={
            pausedAccounts > 0
              ? `${pausedAccounts} account(s) need attention`
              : "All accounts operational"
          }
          icon={Megaphone}
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Campaigns sending now</CardTitle>
            <Link href="/campaigns">
              <Button variant="ghost" size="sm">
                View all
                <ArrowRight className="h-3.5 w-3.5" />
              </Button>
            </Link>
          </CardHeader>
          <CardContent className="pt-2">
            {campaigns.length === 0 ? (
              <EmptyState
                compact
                icon={Megaphone}
                title="No active campaigns"
                description="Start a campaign to begin sending outreach emails automatically."
                action={
                  <Link href="/campaigns">
                    <Button size="sm">Go to campaigns</Button>
                  </Link>
                }
              />
            ) : (
              <ul className="divide-y divide-border-subtle">
                {campaigns.map((campaign) => (
                  <li
                    key={campaign.id}
                    className="flex items-center justify-between gap-4 py-3.5 first:pt-0 last:pb-0"
                  >
                    <div className="min-w-0">
                      <Link
                        href={`/campaigns/${campaign.id}`}
                        className="truncate font-medium text-foreground transition-colors hover:text-brand"
                      >
                        {campaign.name}
                      </Link>
                      <p className="mt-0.5 text-xs text-muted-foreground">
                        {formatNumber(campaignEmailsSent(campaign))} sent ·{" "}
                        {formatNumber(campaignReplies(campaign))} replies
                      </p>
                    </div>
                    <StatusBadge status={campaign.status} />
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Account health</CardTitle>
            <Link href="/health">
              <Button variant="ghost" size="sm">
                Details
                <ArrowRight className="h-3.5 w-3.5" />
              </Button>
            </Link>
          </CardHeader>
          <CardContent className="pt-2">
            {healthAccounts.length === 0 ? (
              <EmptyState
                compact
                icon={Mail}
                title="No accounts connected"
                description="Connect a Gmail account to start sending outreach."
                action={
                  <Link href="/accounts/connect">
                    <Button size="sm">Connect Gmail</Button>
                  </Link>
                }
              />
            ) : (
              <ul className="divide-y divide-border-subtle">
                {healthAccounts.slice(0, 5).map((account) => (
                  <li
                    key={account.id}
                    className="flex items-center justify-between gap-4 py-3.5 first:pt-0 last:pb-0"
                  >
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium text-foreground">
                        {account.email}
                      </p>
                      <div className="mt-1">
                        <HealthBadge score={account.health_score} />
                      </div>
                    </div>
                    <div className="flex items-center gap-2 tabular-nums">
                      <Activity className="h-4 w-4 text-muted-foreground" />
                      <span className="text-sm font-semibold text-foreground">
                        {account.health_score}
                      </span>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
