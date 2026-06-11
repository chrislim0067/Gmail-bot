"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { Megaphone, Plus } from "lucide-react";
import { StatusBadge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { Input } from "@/components/ui/Input";
import { PageHeader } from "@/components/ui/PageHeader";
import { PageLoader } from "@/components/ui/LoadingSpinner";
import { Select } from "@/components/ui/Select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/Table";
import { useIntervalPoll } from "@/hooks/useIntervalPoll";
import { campaignsApi, poolsApi } from "@/lib/api";
import { BACKEND_POLL_MS } from "@/lib/polling";
import { formatNumber } from "@/lib/utils";
import {
  campaignEmailsSent,
  campaignPeopleCount,
  campaignReplies,
} from "@/lib/campaign-display";
import type { AccountPool, Campaign } from "@/types/api";

export default function CampaignsPage() {
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [pools, setPools] = useState<AccountPool[]>([]);
  const [name, setName] = useState("");
  const [poolId, setPoolId] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const loadCampaigns = useCallback(async (options?: { silent?: boolean }) => {
    if (!options?.silent) setLoading(true);
    try {
      const data = await campaignsApi.list({ limit: 50 });
      setCampaigns(data?.items ?? []);
    } catch {
      setCampaigns([]);
    } finally {
      if (!options?.silent) setLoading(false);
    }
  }, []);

  const hasRunning = campaigns.some((c) => c.status === "running");

  useEffect(() => {
    void loadCampaigns();
  }, [loadCampaigns]);

  useIntervalPoll(loadCampaigns, BACKEND_POLL_MS, hasRunning);

  useEffect(() => {
    if (!showForm) return;
    void (async () => {
      const poolsResult = await Promise.allSettled([poolsApi.list()]);
      setPools(
        poolsResult[0].status === "fulfilled"
          ? (poolsResult[0].value.items ?? [])
          : []
      );
    })();
  }, [showForm]);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    try {
      await campaignsApi.create({
        name,
        campaign_account_pool_id: poolId,
      });
      setShowForm(false);
      setName("");
      await loadCampaigns();
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Campaigns"
        description="Create and manage email outreach projects. Track sends, replies, and delivery status."
        actions={
          <Button size="sm" onClick={() => setShowForm(!showForm)}>
            <Plus className="h-4 w-4" />
            New campaign
          </Button>
        }
      />

      {showForm && (
        <Card className="animate-slide-in">
          <CardHeader>
            <CardTitle>Create campaign</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleCreate} className="grid gap-4 sm:grid-cols-2">
              <div className="sm:col-span-2">
                <Input
                  label="Campaign name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  required
                  placeholder="Q2 outreach — SaaS founders"
                />
              </div>
              <div className="sm:col-span-2 rounded-2xl border border-violet-100 bg-violet-50/40 px-4 py-3 text-sm text-muted-foreground">
                Each candidate receives a <strong className="text-foreground">random message template</strong> and{" "}
                <strong className="text-foreground">random subject</strong> from your Outreach content library.
                Their name and email are filled in automatically. &quot;Thanks, Chris&quot; is added to every email.
              </div>
              <Select
                label="Account pool"
                value={poolId}
                onChange={(e) => setPoolId(e.target.value)}
                required
              >
                <option value="">Choose an account group</option>
                {pools.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </Select>
              <div className="flex gap-2 sm:col-span-2">
                <Button type="submit" loading={submitting}>
                  Create campaign
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setShowForm(false)}
                >
                  Cancel
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      )}

      {loading ? (
        <PageLoader />
      ) : (
        <Card>
          {campaigns.length === 0 ? (
            <EmptyState
              icon={Megaphone}
              title="No campaigns yet"
              description="Create your first campaign to start sending compliant cold emails through Gmail."
              action={
                <Button size="sm" onClick={() => setShowForm(true)}>
                  <Plus className="h-4 w-4" />
                  New campaign
                </Button>
              }
            />
          ) : (
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Campaign</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Sent</TableHead>
                    <TableHead>Replies</TableHead>
                    <TableHead>Leads</TableHead>
                    <TableHead className="text-right">Action</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {campaigns.map((campaign) => (
                    <TableRow key={campaign.id}>
                      <TableCell>
                        <Link
                          href={`/campaigns/${campaign.id}`}
                          className="font-medium text-foreground transition-colors hover:text-brand"
                        >
                          {campaign.name}
                        </Link>
                      </TableCell>
                      <TableCell>
                        <StatusBadge status={campaign.status} />
                      </TableCell>
                      <TableCell className="font-medium tabular-nums">
                        {formatNumber(campaignEmailsSent(campaign))}
                      </TableCell>
                      <TableCell className="tabular-nums text-muted-foreground">
                        {formatNumber(campaignReplies(campaign))}
                      </TableCell>
                      <TableCell className="tabular-nums text-muted-foreground">
                        {formatNumber(campaignPeopleCount(campaign))}
                      </TableCell>
                      <TableCell className="text-right">
                        <Link href={`/campaigns/${campaign.id}`}>
                          <Button variant="ghost" size="sm">
                            Open
                          </Button>
                        </Link>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          )}
        </Card>
      )}
    </div>
  );
}
