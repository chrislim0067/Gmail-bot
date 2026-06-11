"use client";

import { useEffect, useState } from "react";
import { AlertCircle, HeartPulse } from "lucide-react";
import { DataCard, Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { TierBadge, RiskBadge, HealthBadge } from "@/components/ui/Badge";
import { Alert } from "@/components/ui/Alert";
import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";
import { PageLoader } from "@/components/ui/LoadingSpinner";
import { healthApi } from "@/lib/api";
import { formatDate, formatPercent } from "@/lib/utils";
import type { HealthAccount, HealthEvent } from "@/types/api";

export default function HealthPage() {
  const [accounts, setAccounts] = useState<HealthAccount[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [events, setEvents] = useState<HealthEvent[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    healthApi.accounts().then((data) => {
      setAccounts(data.items);
      setLoading(false);
    });
  }, []);

  useEffect(() => {
    if (selectedId) {
      healthApi.events(selectedId).then((data) => setEvents(data.items));
    }
  }, [selectedId]);

  if (loading) {
    return <PageLoader />;
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Account Health"
        description="Health scores, bounce rates, and event timelines"
      />

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {accounts.length === 0 ? (
          <Card className="col-span-full">
            <CardContent>
              <EmptyState
                icon={HeartPulse}
                title="No accounts to monitor"
                description="Connect Gmail accounts to start tracking health metrics."
              />
            </CardContent>
          </Card>
        ) : (
          accounts.map((account) => (
            <DataCard
              key={account.id}
              className={`cursor-pointer ${
                selectedId === account.id ? "ring-2 ring-brand" : ""
              }`}
              onClick={() => setSelectedId(account.id)}
            >
              <CardHeader className="flex flex-row items-start justify-between">
                <div>
                  <CardTitle className="text-base">{account.email}</CardTitle>
                  <div className="mt-2 flex flex-wrap gap-2">
                    <TierBadge tier={account.account_tier} />
                    <RiskBadge level={account.risk_level} />
                  </div>
                </div>
                <div className="text-right">
                  <p
                    className={`text-2xl font-semibold tabular-nums ${
                      account.health_score >= 70
                        ? "text-success"
                        : account.health_score >= 40
                          ? "text-warning"
                          : "text-danger"
                    }`}
                  >
                    {account.health_score}
                  </p>
                  <HealthBadge score={account.health_score} />
                </div>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 gap-2 text-sm">
                  <div>
                    <p className="text-xs text-muted-foreground">Bounce (7d)</p>
                    <p className="font-medium">{formatPercent(account.bounce_rate_7d)}</p>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground">Error (7d)</p>
                    <p className="font-medium">{formatPercent(account.error_rate_7d)}</p>
                  </div>
                </div>
                {account.alerts && account.alerts.length > 0 && (
                  <Alert variant="warning" className="mt-3" icon={AlertCircle}>
                    {account.alerts[0]}
                  </Alert>
                )}
              </CardContent>
            </DataCard>
          ))
        )}
      </div>

      {selectedId && (
        <Card>
          <CardHeader>
            <CardTitle>Health event timeline</CardTitle>
          </CardHeader>
          <CardContent>
            {events.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                No health events recorded.
              </p>
            ) : (
              <ul className="space-y-3">
                {events.map((event) => (
                  <li
                    key={event.id}
                    className="flex items-start gap-3 border-b border-border-subtle pb-3 last:border-0"
                  >
                    <div
                      className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${
                        event.severity === "high"
                          ? "bg-danger"
                          : event.severity === "medium"
                            ? "bg-warning"
                            : "bg-stone-300"
                      }`}
                    />
                    <div>
                      <p className="text-sm font-medium text-foreground">
                        {event.event_type}
                      </p>
                      <p className="text-sm text-muted-foreground">{event.message}</p>
                      <p className="mt-1 text-xs text-muted-foreground">
                        {formatDate(event.created_at)}
                      </p>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
