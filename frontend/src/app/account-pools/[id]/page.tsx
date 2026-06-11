"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft, Plus, Trash2, UserPlus, Users } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Badge, ActiveBadge } from "@/components/ui/Badge";
import { Alert } from "@/components/ui/Alert";
import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";
import { PageLoader } from "@/components/ui/LoadingSpinner";
import { Select } from "@/components/ui/Select";
import { gmailApi, poolsApi } from "@/lib/api";
import type { AccountPoolDetail, GmailAccount } from "@/types/api";

export default function AccountPoolDetailPage() {
  const params = useParams();
  const poolId = params.id as string;

  const [pool, setPool] = useState<AccountPoolDetail | null>(null);
  const [accounts, setAccounts] = useState<GmailAccount[]>([]);
  const [selectedAccountId, setSelectedAccountId] = useState("");
  const [loading, setLoading] = useState(true);
  const [adding, setAdding] = useState(false);
  const [error, setError] = useState("");

  async function loadData() {
    setLoading(true);
    try {
      const [poolData, accountsData] = await Promise.all([
        poolsApi.get(poolId),
        gmailApi.listAccounts(),
      ]);
      setPool(poolData);
      setAccounts(accountsData.items ?? []);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
  }, [poolId]);

  const memberIds = new Set(pool?.members.map((m) => m.gmail_account_id) ?? []);
  const availableAccounts = accounts.filter(
    (a) => a.status === "active" && !memberIds.has(a.id)
  );

  function emailForMember(gmailAccountId: string) {
    return accounts.find((a) => a.id === gmailAccountId)?.email ?? gmailAccountId;
  }

  async function handleAddMember(e: React.FormEvent) {
    e.preventDefault();
    if (!selectedAccountId) return;
    setAdding(true);
    setError("");
    try {
      await poolsApi.addMember(poolId, { gmail_account_id: selectedAccountId });
      setSelectedAccountId("");
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to add account");
    } finally {
      setAdding(false);
    }
  }

  async function handleRemoveMember(accountId: string) {
    setError("");
    try {
      await poolsApi.removeMember(poolId, accountId);
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to remove account");
    }
  }

  if (loading) {
    return <PageLoader />;
  }

  if (!pool) {
    return (
      <EmptyState
        icon={Users}
        title="Pool not found"
        description="This account pool may have been deleted or the link is invalid."
        action={
          <Link href="/account-pools">
            <Button variant="outline" size="sm">
              Back to pools
            </Button>
          </Link>
        }
      />
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <Link
          href="/account-pools"
          className="mb-3 inline-flex items-center gap-1 text-sm text-muted-foreground transition-colors hover:text-brand"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to pools
        </Link>
        <PageHeader
          title={pool.name}
          description={pool.description}
          badge={<Badge variant="info">{pool.status ?? "active"}</Badge>}
        />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Add Gmail account to pool</CardTitle>
        </CardHeader>
        <CardContent>
          {accounts.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No Gmail accounts connected.{" "}
              <Link href="/accounts/connect" className="text-brand underline">
                Connect Gmail
              </Link>{" "}
              first.
            </p>
          ) : availableAccounts.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              All active Gmail accounts are already in this pool.
            </p>
          ) : (
            <form onSubmit={handleAddMember} className="flex flex-wrap items-end gap-3">
              <Select
                label="Gmail account"
                value={selectedAccountId}
                onChange={(e) => setSelectedAccountId(e.target.value)}
                required
                className="min-w-[240px] flex-1"
              >
                <option value="">Select Gmail account</option>
                {availableAccounts.map((account) => (
                  <option key={account.id} value={account.id}>
                    {account.email}
                  </option>
                ))}
              </Select>
              <Button type="submit" loading={adding}>
                <Plus className="h-4 w-4" />
                Add to pool
              </Button>
            </form>
          )}
          {error && (
            <Alert variant="danger" className="mt-3" onDismiss={() => setError("")}>
              {error}
            </Alert>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Pool members ({pool.members.length})</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {pool.members.length === 0 ? (
            <EmptyState
              icon={UserPlus}
              title="No accounts in this pool"
              description="Add at least one active Gmail account before starting a campaign."
              compact
            />
          ) : (
            <ul className="divide-y divide-border-subtle">
              {pool.members.map((member) => (
                <li
                  key={member.id}
                  className="flex items-center justify-between px-5 py-4 sm:px-6"
                >
                  <div>
                    <p className="font-medium text-foreground">
                      {emailForMember(member.gmail_account_id)}
                    </p>
                    <div className="mt-1 flex items-center gap-2 text-xs text-muted-foreground">
                      <span>Priority {member.priority}</span>
                      <ActiveBadge active={member.is_active} />
                    </div>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleRemoveMember(member.gmail_account_id)}
                  >
                    <Trash2 className="h-4 w-4" />
                    Remove
                  </Button>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
