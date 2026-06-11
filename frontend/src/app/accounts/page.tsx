"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Mail, Pause, Play, RefreshCw, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { DataCard, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { ActiveBadge, Badge, RiskBadge, TierBadge } from "@/components/ui/Badge";
import { Alert } from "@/components/ui/Alert";
import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";
import { Input } from "@/components/ui/Input";
import { PageLoader } from "@/components/ui/LoadingSpinner";
import { StatCard } from "@/components/ui/StatCard";
import { gmailApi } from "@/lib/api";
import { formatDate, formatPercent } from "@/lib/utils";
import { SendTimeline, useAccountSendTimeline } from "@/components/send/SendTimeline";
import type { GmailAccount } from "@/types/api";

export default function AccountsPage() {
  const searchParams = useSearchParams();
  const [accounts, setAccounts] = useState<GmailAccount[]>([]);
  const [loading, setLoading] = useState(true);
  const { timeline, loading: timelineLoading } = useAccountSendTimeline();
  const [actionId, setActionId] = useState<string | null>(null);
  const [limitDrafts, setLimitDrafts] = useState<Record<string, string>>({});
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  async function loadAccounts() {
    setLoading(true);
    try {
      const data = await gmailApi.listAccounts();
      setAccounts(data.items);
      setLimitDrafts(
        Object.fromEntries(
          data.items.map((account) => [
            account.id,
            String(
              account.effective_daily_send_limit ?? account.daily_send_limit
            ),
          ])
        )
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadAccounts();
  }, []);

  useEffect(() => {
    if (searchParams.get("connected") === "1") {
      setMessage("Gmail account connected successfully.");
      loadAccounts();
    }
    const oauthError = searchParams.get("error");
    if (oauthError) {
      setError(`Google sign-in failed: ${oauthError}`);
    }
  }, [searchParams]);

  async function togglePause(account: GmailAccount) {
    setActionId(account.id);
    try {
      if (account.status === "paused") {
        await gmailApi.resumeAccount(account.id);
      } else {
        await gmailApi.pauseAccount(account.id);
      }
      await loadAccounts();
    } finally {
      setActionId(null);
    }
  }

  async function saveDailyLimit(account: GmailAccount) {
    const raw = limitDrafts[account.id] ?? String(account.daily_send_limit);
    const next = parseInt(raw, 10);
    if (Number.isNaN(next) || next < 1) {
      setError("Daily target must be at least 1.");
      return;
    }
    if (next > account.tier_daily_hard_max) {
      setError(
        `${account.email} can send at most ${account.tier_daily_hard_max}/day on the ${account.account_tier} tier.`
      );
      return;
    }
    setActionId(account.id);
    setError("");
    try {
      await gmailApi.updateAccount(account.id, { daily_send_limit: next });
      setMessage(`Daily target for ${account.email} set to ${next}.`);
      await loadAccounts();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update daily target.");
    } finally {
      setActionId(null);
    }
  }

  async function removeAccount(account: GmailAccount) {
    if (
      !confirm(
        `Remove ${account.email} from this platform? You can reconnect it later.`
      )
    ) {
      return;
    }
    setActionId(account.id);
    try {
      await gmailApi.revokeAccount(account.id);
      setMessage(`Removed ${account.email}.`);
      await loadAccounts();
    } catch {
      setError("Failed to remove account.");
    } finally {
      setActionId(null);
    }
  }

  async function removeMockAccounts() {
    const mockCount = accounts.filter((a) =>
      a.email.startsWith("mock.user.")
    ).length;
    if (mockCount === 0) {
      setMessage("No mock accounts to remove.");
      return;
    }
    if (
      !confirm(
        `Remove all ${mockCount} mock test accounts? This cannot be undone.`
      )
    ) {
      return;
    }
    try {
      const result = await gmailApi.purgeMockAccounts();
      setMessage(`Removed mock accounts (${result.status}).`);
      await loadAccounts();
    } catch {
      setError("Failed to remove mock accounts.");
    }
  }

  const hasMockAccounts = accounts.some((a) => a.email.startsWith("mock.user."));

  return (
    <div className="space-y-6">
      <PageHeader
        title="Gmail Accounts"
        description="Manage connected inboxes, tiers, and send limits"
        actions={
          <>
            {hasMockAccounts && (
              <Button variant="outline" size="sm" onClick={removeMockAccounts}>
                <Trash2 className="h-4 w-4" />
                Remove mock accounts
              </Button>
            )}
            <Button variant="outline" size="sm" onClick={loadAccounts}>
              <RefreshCw className="h-4 w-4" />
              Refresh
            </Button>
            <Link href="/accounts/connect">
              <Button size="sm">Connect Gmail</Button>
            </Link>
          </>
        }
      />

      {message && (
        <Alert variant="success" onDismiss={() => setMessage("")}>
          {message}
        </Alert>
      )}
      {error && (
        <Alert variant="danger" onDismiss={() => setError("")}>
          {error}
        </Alert>
      )}

      <SendTimeline timeline={timeline} loading={timelineLoading} compact />

      {loading ? (
        <PageLoader />
      ) : accounts.length === 0 ? (
        <DataCard>
          <CardContent>
            <EmptyState
              icon={Mail}
              title="No Gmail accounts connected"
              description="Connect your first Gmail account to start sending outreach campaigns."
              action={
                <Link href="/accounts/connect">
                  <Button>Connect your first account</Button>
                </Link>
              }
            />
          </CardContent>
        </DataCard>
      ) : (
        <div className="grid gap-4">
          {accounts.map((account) => (
            <DataCard key={account.id}>
              <CardHeader className="flex flex-row items-start justify-between">
                <div>
                  <CardTitle className="text-base">{account.email}</CardTitle>
                  <div className="mt-2 flex flex-wrap gap-2">
                    <TierBadge tier={account.account_tier} />
                    <RiskBadge level={account.risk_level} />
                    {account.status === "active" ? (
                      <ActiveBadge active />
                    ) : account.status === "paused" ? (
                      <ActiveBadge active={false} />
                    ) : (
                      <Badge
                        variant={
                          account.status === "auth_error" ? "danger" : "warning"
                        }
                      >
                        {account.status}
                      </Badge>
                    )}
                    {account.review_required && (
                      <Badge variant="danger">Review required</Badge>
                    )}
                  </div>
                </div>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    loading={actionId === account.id}
                    onClick={() => togglePause(account)}
                    disabled={account.status === "auth_error"}
                  >
                    {account.status === "paused" ? (
                      <>
                        <Play className="h-4 w-4" /> Resume
                      </>
                    ) : (
                      <>
                        <Pause className="h-4 w-4" /> Pause
                      </>
                    )}
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    loading={actionId === account.id}
                    onClick={() => removeAccount(account)}
                  >
                    <Trash2 className="h-4 w-4" /> Remove
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                  <StatCard
                    title="Health score"
                    value={account.health_score}
                    className="p-4"
                  />
                  <StatCard
                    title="Sent today / target"
                    value={`${account.sent_today} / ${account.effective_daily_send_limit ?? account.daily_send_limit}`}
                    subtitle={
                      account.remaining_today != null
                        ? `${account.remaining_today} sends left today`
                        : undefined
                    }
                    className="p-4"
                  />
                  <StatCard
                    title="Bounce rate (7d)"
                    value={formatPercent(account.bounce_rate_7d)}
                    className="p-4"
                  />
                  <StatCard
                    title="Success streak"
                    value={`${account.consecutive_success_days} days`}
                    className="p-4"
                  />
                </div>
                <form
                  className="mt-4 flex flex-wrap items-end gap-3 border-t border-border-subtle pt-4"
                  onSubmit={(e) => {
                    e.preventDefault();
                    void saveDailyLimit(account);
                  }}
                >
                  <Input
                    label="Daily send target"
                    type="number"
                    min={1}
                    max={account.tier_daily_hard_max}
                    value={limitDrafts[account.id] ?? String(account.daily_send_limit)}
                    onChange={(e) =>
                      setLimitDrafts((prev) => ({
                        ...prev,
                        [account.id]: e.target.value,
                      }))
                    }
                    hint={`Tier max ${account.tier_daily_hard_max}/day · default ${account.tier_daily_default}`}
                    className="max-w-[180px]"
                  />
                  <Button
                    type="submit"
                    size="sm"
                    variant="outline"
                    loading={actionId === account.id}
                  >
                    Save target
                  </Button>
                </form>
                <div className="mt-4 text-xs text-muted-foreground">
                  Connected {formatDate(account.connected_at)} · Tier max{" "}
                  {account.tier_daily_hard_max}/day · Scopes:{" "}
                  {account.granted_scopes?.join(", ") || "—"}
                </div>
                {account.review_required && (
                  <Link
                    href="/accounts/review"
                    className="mt-3 inline-block text-sm font-medium text-brand hover:underline"
                  >
                    Submit for review →
                  </Link>
                )}
              </CardContent>
            </DataCard>
          ))}
        </div>
      )}
    </div>
  );
}
