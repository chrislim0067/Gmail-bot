"use client";

import { useEffect, useState } from "react";
import {
  BarChart3,
  Mail,
  MessageSquare,
  TrendingDown,
  UserMinus,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { StatCard } from "@/components/ui/StatCard";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { ProgressBar } from "@/components/ui/ProgressBar";
import { PageHeader } from "@/components/ui/PageHeader";
import { PageLoader } from "@/components/ui/LoadingSpinner";
import { analyticsApi } from "@/lib/api";
import { formatNumber, formatPercent } from "@/lib/utils";
import type { AnalyticsOverview } from "@/types/api";

export default function AnalyticsPage() {
  const [overview, setOverview] = useState<AnalyticsOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");

  async function loadAnalytics() {
    setLoading(true);
    try {
      const data = await analyticsApi.overview({
        from: dateFrom || undefined,
        to: dateTo || undefined,
      });
      setOverview(data);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadAnalytics();
  }, []);

  const funnelItems = [
    { label: "Sent", value: overview?.sent ?? 0, variant: "default" as const },
    { label: "Replied", value: overview?.replied ?? 0, variant: "success" as const },
    { label: "Bounced", value: overview?.bounced ?? 0, variant: "danger" as const },
    {
      label: "Unsubscribed",
      value: overview?.unsubscribed ?? 0,
      variant: "warning" as const,
    },
  ];

  const maxSent = overview?.sent || 1;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Analytics"
        description="Outreach performance metrics and trends"
        actions={
          <div className="flex flex-wrap items-end gap-2">
            <Input
              label="From"
              type="date"
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
              className="w-auto"
            />
            <Input
              label="To"
              type="date"
              value={dateTo}
              onChange={(e) => setDateTo(e.target.value)}
              className="w-auto"
            />
            <Button size="sm" onClick={loadAnalytics}>
              Apply
            </Button>
          </div>
        }
      />

      {loading ? (
        <PageLoader />
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
            <StatCard
              title="Sent"
              value={formatNumber(overview?.sent ?? 0)}
              icon={Mail}
            />
            <StatCard
              title="Replied"
              value={formatNumber(overview?.replied ?? 0)}
              icon={MessageSquare}
            />
            <StatCard
              title="Bounced"
              value={formatNumber(overview?.bounced ?? 0)}
              icon={TrendingDown}
            />
            <StatCard
              title="Unsubscribed"
              value={formatNumber(overview?.unsubscribed ?? 0)}
              icon={UserMinus}
            />
            <StatCard
              title="Reply rate"
              value={formatPercent(overview?.reply_rate ?? 0)}
              icon={BarChart3}
            />
            <StatCard
              title="Bounce rate"
              value={formatPercent(overview?.bounce_rate ?? 0)}
              icon={TrendingDown}
            />
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Performance summary</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid gap-6 md:grid-cols-2">
                <div>
                  <h4 className="text-sm font-medium text-foreground">
                    Engagement funnel
                  </h4>
                  <div className="mt-4 space-y-4">
                    {funnelItems.map(({ label, value, variant }) => (
                      <ProgressBar
                        key={label}
                        label={`${label} — ${formatNumber(value)}`}
                        value={value}
                        max={maxSent}
                        variant={variant}
                      />
                    ))}
                  </div>
                </div>
                <div className="rounded-2xl border border-border-subtle bg-gradient-to-br from-stone-50 to-violet-50/30 p-5 text-sm text-muted-foreground">
                  <p className="font-medium text-foreground">Key rates</p>
                  <ul className="mt-3 space-y-2">
                    <li>
                      Reply rate:{" "}
                      <strong className="text-foreground">
                        {formatPercent(overview?.reply_rate ?? 0)}
                      </strong>
                    </li>
                    <li>
                      Bounce rate:{" "}
                      <strong className="text-foreground">
                        {formatPercent(overview?.bounce_rate ?? 0)}
                      </strong>
                    </li>
                    <li>
                      Unsubscribe rate:{" "}
                      <strong className="text-foreground">
                        {overview?.sent
                          ? formatPercent(
                              (overview.unsubscribed ?? 0) / overview.sent
                            )
                          : "—"}
                      </strong>
                    </li>
                  </ul>
                </div>
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
