"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  CheckCircle2,
  Mail,
  Pause,
  Play,
  RefreshCw,
  ShieldCheck,
  XCircle,
} from "lucide-react";
import { Alert } from "@/components/ui/Alert";
import { StatusBadge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { PageLoader } from "@/components/ui/LoadingSpinner";
import { PageHeader } from "@/components/ui/PageHeader";
import { StatCard } from "@/components/ui/StatCard";
import { ApiClientError, campaignsApi } from "@/lib/api";
import { formatDate, formatNumber } from "@/lib/utils";
import { SendHistoryTable } from "@/components/send/SendHistoryTable";
import { SendTimeline, useAccountSendTimeline } from "@/components/send/SendTimeline";
import { useIntervalPoll } from "@/hooks/useIntervalPoll";
import { BACKEND_POLL_MS } from "@/lib/polling";
import type { Campaign, PreflightCheck, SendJob } from "@/types/api";

export default function CampaignDetailPage() {
  const params = useParams();
  const id = params.id as string;

  const [campaign, setCampaign] = useState<Campaign | null>(null);
  const [sendJobs, setSendJobs] = useState<SendJob[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState(false);
  const [showPreflight, setShowPreflight] = useState(false);
  const [preflight, setPreflight] = useState<PreflightCheck | null>(null);
  const [preflightLoading, setPreflightLoading] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [refreshError, setRefreshError] = useState<string | null>(null);
  const [completionNotice, setCompletionNotice] = useState<string | null>(null);
  const prevStatusRef = useRef<string | null>(null);
  const isRunning = campaign?.status === "running";
  const { timeline, loading: timelineLoading } = useAccountSendTimeline(
    BACKEND_POLL_MS,
    0,
    isRunning
  );

  const loadCampaign = useCallback(
    async (options?: { silent?: boolean }) => {
      try {
        const data = await campaignsApi.get(id);
        setCampaign(data);
        setLoadError(null);
        setRefreshError(null);
        setActionError(null);
        return data;
      } catch (err) {
        const message =
          err instanceof ApiClientError
            ? err.message
            : "Failed to load campaign.";
        if (options?.silent) {
          setRefreshError(message);
        } else {
          setLoadError(message);
        }
        return null;
      } finally {
        setLoading(false);
      }
    },
    [id]
  );

  const loadSendJobs = useCallback(async () => {
    try {
      const data = await campaignsApi.sendJobs(id, { limit: 50 });
      setSendJobs(data.items);
    } catch {
      setSendJobs([]);
    }
  }, [id]);

  const refreshActivity = useCallback(
    async (options?: { silent?: boolean }) => {
      await loadCampaign(options);
      await loadSendJobs();
    },
    [loadCampaign, loadSendJobs]
  );

  useEffect(() => {
    setLoading(true);
    void refreshActivity();
  }, [refreshActivity]);

  useIntervalPoll(refreshActivity, BACKEND_POLL_MS, isRunning);

  useEffect(() => {
    if (!campaign) return;
    const prev = prevStatusRef.current;
    if (prev === "running" && campaign.status === "completed") {
      setCompletionNotice(
        "All emails have been sent. This campaign has ended automatically."
      );
    }
    prevStatusRef.current = campaign.status;
  }, [campaign?.status]);

  async function runPreflight() {
    setPreflightLoading(true);
    setShowPreflight(true);
    try {
      const result = await campaignsApi.preflightCheck(id);
      setPreflight(result);
      if (result.passed) {
        await refreshActivity();
      }
    } finally {
      setPreflightLoading(false);
    }
  }

  async function handleStart() {
    setActionLoading(true);
    setActionError(null);
    try {
      await campaignsApi.start(id);
      await refreshActivity();
    } catch (err) {
      setActionError(
        err instanceof ApiClientError
          ? err.message
          : "Failed to start campaign."
      );
    } finally {
      setActionLoading(false);
      setShowPreflight(false);
    }
  }

  async function handlePause() {
    setActionLoading(true);
    setActionError(null);
    try {
      await campaignsApi.pause(id);
      await refreshActivity();
    } catch (err) {
      setActionError(
        err instanceof ApiClientError
          ? err.message
          : "Failed to pause campaign."
      );
    } finally {
      setActionLoading(false);
    }
  }

  async function handleResume() {
    setActionLoading(true);
    setActionError(null);
    try {
      await campaignsApi.resume(id);
      await refreshActivity();
    } catch (err) {
      setActionError(
        err instanceof ApiClientError
          ? err.message
          : "Failed to resume campaign."
      );
    } finally {
      setActionLoading(false);
    }
  }

  async function handleProcessNow() {
    setActionLoading(true);
    setActionError(null);
    try {
      await campaignsApi.processQueue(id);
      await refreshActivity();
    } catch (err) {
      setActionError(
        err instanceof ApiClientError
          ? err.message
          : "Failed to process send queue."
      );
    } finally {
      setActionLoading(false);
    }
  }

  if (loading) return <PageLoader />;

  if (loadError) {
    return (
      <div className="space-y-4">
        <Alert variant="danger" title="Could not load campaign">
          {loadError} Run{" "}
          <code className="rounded bg-zinc-100 px-1.5 py-0.5 text-xs">
            GmailOutreach-Start.bat
          </code>{" "}
          and keep all four service windows open.
        </Alert>
        <div className="flex gap-2">
          <Button onClick={() => { setLoading(true); void refreshActivity(); }}>
            <RefreshCw className="h-4 w-4" />
            Retry
          </Button>
          <Link href="/campaigns">
            <Button variant="outline">Back to campaigns</Button>
          </Link>
        </div>
      </div>
    );
  }

  if (!campaign) {
    return (
      <div className="space-y-4">
        <p className="text-slate-500">Campaign not found.</p>
        <Link href="/campaigns">
          <Button variant="outline">Back to campaigns</Button>
        </Link>
      </div>
    );
  }

  const stats = campaign.stats;
  const waitingToSend = (stats?.pending ?? 0) + (stats?.queued ?? 0);

  const statusDescription =
    campaign.status === "running"
      ? waitingToSend === 0
        ? "All leads have been emailed — finishing this campaign…"
        : "Sending emails automatically — this page updates on its own."
      : campaign.status === "completed"
        ? "Finished — every lead on this list has been emailed."
        : campaign.status === "paused"
          ? "Paused — click Resume to continue sending."
          : campaign.status === "draft"
            ? "Not started yet — run a safety check, then click Start."
            : `Scheduled for ${formatDate(campaign.scheduled_start_at)}`;

  return (
    <div className="space-y-6">
      {completionNotice && (
        <Alert
          variant="success"
          onDismiss={() => setCompletionNotice(null)}
        >
          {completionNotice}
        </Alert>
      )}
      {(actionError || refreshError) && (
        <Alert
          variant="danger"
          onDismiss={() => {
            setActionError(null);
            setRefreshError(null);
          }}
        >
          {actionError ?? refreshError}
        </Alert>
      )}

      <PageHeader
        title={campaign.name}
        description={statusDescription}
        badge={<StatusBadge status={campaign.status} />}
        actions={
          <>
            <Button variant="outline" onClick={runPreflight} loading={preflightLoading}>
              <ShieldCheck className="h-4 w-4" />
              Safety check
            </Button>
            {(campaign.status === "draft" || campaign.status === "scheduled") && (
              <Button
                onClick={handleStart}
                loading={actionLoading}
                disabled={!campaign.preflight_passed_at}
              >
                <Play className="h-4 w-4" />
                Start
              </Button>
            )}
            {campaign.status === "running" && (
              <>
                <Button
                  variant="outline"
                  onClick={handleProcessNow}
                  loading={actionLoading}
                >
                  <RefreshCw className="h-4 w-4" />
                  Send now
                </Button>
                <Button variant="secondary" onClick={handlePause} loading={actionLoading}>
                  <Pause className="h-4 w-4" />
                  Pause
                </Button>
              </>
            )}
            {campaign.status === "paused" && (
              <Button onClick={handleResume} loading={actionLoading}>
                <Play className="h-4 w-4" />
                Resume
              </Button>
            )}
            <Link href={`/campaigns/${id}/leads`}>
              <Button variant="outline">Manage leads</Button>
            </Link>
          </>
        }
      />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Waiting to send"
          value={formatNumber(waitingToSend)}
          subtitle="Leads not emailed yet"
        />
        <StatCard
          title="Sent"
          value={formatNumber(stats?.sent ?? 0)}
          subtitle="Emails delivered"
        />
        <StatCard
          title="Replies"
          value={formatNumber(stats?.replied ?? 0)}
          subtitle="People who wrote back"
        />
        <StatCard
          title="Needs attention"
          value={formatNumber((stats?.failed ?? 0) + (stats?.bounced ?? 0))}
          subtitle="Failed or bounced"
        />
      </div>

      <SendTimeline timeline={timeline} loading={timelineLoading} compact />

      <Card>
        <CardHeader>
          <CardTitle>Recent emails</CardTitle>
          <p className="text-sm font-normal text-slate-500">
            Who was emailed and whether it went out successfully
          </p>
        </CardHeader>
        <CardContent className="p-0">
          {sendJobs.length === 0 ? (
            <EmptyState
              compact
              icon={Mail}
              title="No emails yet"
              description="Add people under Manage leads, then start the campaign."
            />
          ) : (
            <SendHistoryTable jobs={sendJobs} />
          )}
        </CardContent>
      </Card>

      {showPreflight && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-zinc-950/50 p-4 backdrop-blur-sm">
          <Card className="w-full max-w-lg shadow-elevated animate-slide-in">
            <CardHeader>
              <CardTitle>Preflight check results</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {preflightLoading ? (
                <div className="flex justify-center py-8">
                  <div className="h-8 w-8 animate-spin rounded-full border-2 border-brand border-t-transparent" />
                </div>
              ) : preflight ? (
                <>
                  <div
                    className={`flex items-center gap-2 rounded-lg p-3 text-sm font-medium ${
                      preflight.passed
                        ? "bg-emerald-50 text-emerald-800"
                        : "bg-red-50 text-red-800"
                    }`}
                  >
                    {preflight.passed ? (
                      <CheckCircle2 className="h-5 w-5" />
                    ) : (
                      <XCircle className="h-5 w-5" />
                    )}
                    {preflight.passed
                      ? "All checks passed — ready to start"
                      : "Preflight failed — fix issues before starting"}
                  </div>
                  <ul className="space-y-2">
                    {preflight.checks.map((check) => (
                      <li
                        key={check.name}
                        className="flex items-start gap-2 text-sm"
                      >
                        {check.passed ? (
                          <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-500" />
                        ) : (
                          <XCircle className="mt-0.5 h-4 w-4 shrink-0 text-red-500" />
                        )}
                        <div>
                          <p className="font-medium capitalize">
                            {check.name.replace(/_/g, " ")}
                          </p>
                          <p className="text-slate-500">{check.message}</p>
                        </div>
                      </li>
                    ))}
                  </ul>
                </>
              ) : null}
              <div className="flex justify-end gap-2">
                <Button variant="outline" onClick={() => setShowPreflight(false)}>
                  Close
                </Button>
                {preflight?.passed && (
                  <Button onClick={handleStart} loading={actionLoading}>
                    Start campaign
                  </Button>
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
