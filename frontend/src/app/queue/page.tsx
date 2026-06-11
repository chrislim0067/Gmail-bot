"use client";

import { useCallback, useEffect, useState } from "react";
import { Clock, Inbox, Lock, RotateCcw, Send, XCircle } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { StatCard } from "@/components/ui/StatCard";
import { Alert } from "@/components/ui/Alert";
import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";
import { PageLoader } from "@/components/ui/LoadingSpinner";
import { queueApi, campaignsApi } from "@/lib/api";
import { SendHistoryTable } from "@/components/send/SendHistoryTable";
import { SendTimeline, useAccountSendTimeline } from "@/components/send/SendTimeline";
import { useIntervalPoll } from "@/hooks/useIntervalPoll";
import { BACKEND_POLL_MS } from "@/lib/polling";
import type { QueueStats, SendJob } from "@/types/api";

export default function QueuePage() {
  const [stats, setStats] = useState<QueueStats | null>(null);
  const [jobs, setJobs] = useState<SendJob[]>([]);
  const [loading, setLoading] = useState(true);
  const [resetting, setResetting] = useState(false);
  const [resetMessage, setResetMessage] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);
  const { timeline, loading: timelineLoading } = useAccountSendTimeline(
    BACKEND_POLL_MS,
    refreshKey
  );

  const load = useCallback(async (options?: { silent?: boolean }) => {
    if (!options?.silent) setLoading(true);
    try {
      const statsData = await queueApi.stats();
      setStats(statsData);

      const campaigns = await campaignsApi.list({ status: "running", limit: 5 });
      const allJobs: SendJob[] = [];
      for (const campaign of campaigns.items) {
        const jobData = await campaignsApi
          .sendJobs(campaign.id, { limit: 20 })
          .catch(() => ({ items: [] }));
        allJobs.push(...jobData.items);
      }
      setJobs(allJobs.slice(0, 50));
    } catch {
      // 401 redirects to login in apiFetch; other errors keep the last good data.
    } finally {
      if (!options?.silent) setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load, refreshKey]);

  useIntervalPoll(load, BACKEND_POLL_MS);

  async function handleResetHistory() {
    if (
      !window.confirm(
        "Reset ALL send history? This pauses campaigns, deletes sent records and jobs, clears account timers and Redis limits. Type OK in the next dialog."
      )
    ) {
      return;
    }
    const typed = window.prompt('Type RESET to confirm clearing all send history:');
    if (typed !== "RESET") return;

    setResetting(true);
    setResetMessage(null);
    try {
      const result = await queueApi.resetSendHistory();
      setResetMessage(
        `Reset complete — ${result.campaigns_reset} campaign(s) paused, Redis keys cleared. Click Resume on your campaign to retest.`
      );
      setRefreshKey((k) => k + 1);
      await load();
    } catch (err) {
      setResetMessage(
        err instanceof Error ? err.message : "Failed to reset send history."
      );
    } finally {
      setResetting(false);
    }
  }

  if (loading) {
    return <PageLoader />;
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Send queue"
        description="See which accounts are sending and what is waiting to go out"
        actions={
          <Button
            variant="outline"
            size="sm"
            loading={resetting}
            onClick={handleResetHistory}
          >
            <RotateCcw className="h-4 w-4" />
            Reset & start over
          </Button>
        }
      />

      {resetMessage && (
        <Alert
          variant={resetMessage.includes("Failed") ? "danger" : "info"}
          onDismiss={() => setResetMessage(null)}
        >
          {resetMessage}
        </Alert>
      )}

      <SendTimeline timeline={timeline} loading={timelineLoading} />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Waiting to send"
          value={stats?.pending ?? 0}
          icon={Clock}
        />
        <StatCard
          title="Sending now"
          value={stats?.locked ?? 0}
          icon={Lock}
        />
        <StatCard
          title="Problems"
          value={stats?.failed ?? 0}
          icon={XCircle}
        />
        <StatCard
          title="Sent today"
          value={stats?.sent_today ?? 0}
          icon={Send}
        />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Recent emails</CardTitle>
          <p className="text-sm font-normal text-muted-foreground">
            Latest activity from running campaigns
          </p>
        </CardHeader>
        <CardContent className="p-0">
          {jobs.length === 0 ? (
            <EmptyState
              icon={Inbox}
              title="No send jobs in queue"
              description="Jobs will appear here when campaigns are running."
              compact
            />
          ) : (
            <SendHistoryTable jobs={jobs} />
          )}
        </CardContent>
      </Card>
    </div>
  );
}
