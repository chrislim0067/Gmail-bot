"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Layers, Plus, Users } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { DataCard, Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Badge } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";
import { PageLoader } from "@/components/ui/LoadingSpinner";
import { poolsApi } from "@/lib/api";
import { formatNumber } from "@/lib/utils";
import type { AccountPool } from "@/types/api";

export default function AccountPoolsPage() {
  const [pools, setPools] = useState<AccountPool[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function loadPools() {
    setLoading(true);
    try {
      const data = await poolsApi.list();
      setPools(data?.items ?? []);
    } catch {
      setPools([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadPools();
  }, []);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    try {
      await poolsApi.create({ name, description });
      setName("");
      setDescription("");
      setShowForm(false);
      await loadPools();
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Account Pools"
        description="Group Gmail accounts for staggered campaign sending"
        actions={
          <Button size="sm" onClick={() => setShowForm(!showForm)}>
            <Plus className="h-4 w-4" />
            New pool
          </Button>
        }
      />

      {showForm && (
        <Card>
          <CardHeader>
            <CardTitle>Create account pool</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleCreate} className="space-y-4">
              <Input
                label="Pool name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
              />
              <Input
                label="Description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
              />
              <div className="flex gap-2">
                <Button type="submit" loading={submitting}>
                  Create pool
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
      ) : pools.length === 0 ? (
        <Card>
          <CardContent>
            <EmptyState
              icon={Layers}
              title="No account pools yet"
              description="Create a pool to assign Gmail accounts to campaigns."
              action={
                <Button size="sm" onClick={() => setShowForm(true)}>
                  <Plus className="h-4 w-4" />
                  Create pool
                </Button>
              }
            />
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {pools.map((pool) => (
            <DataCard key={pool.id}>
              <CardHeader className="flex flex-row items-start justify-between">
                <div>
                  <CardTitle>{pool.name}</CardTitle>
                  {pool.description && (
                    <p className="mt-1 text-sm text-muted-foreground">
                      {pool.description}
                    </p>
                  )}
                </div>
                <Badge variant="info">{pool.status ?? "active"}</Badge>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <p className="text-xs text-muted-foreground">Members</p>
                    <p className="flex items-center gap-1 font-semibold">
                      <Users className="h-4 w-4 text-muted-foreground" />
                      {formatNumber(pool.member_count ?? 0)}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground">Sent today</p>
                    <p className="font-semibold">
                      {formatNumber(pool.sends_today ?? 0)}
                      {pool.max_daily_send != null &&
                        ` / ${pool.max_daily_send}`}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground">This hour</p>
                    <p className="font-semibold">
                      {formatNumber(pool.sends_this_hour ?? 0)}
                      {pool.max_hourly_send != null &&
                        ` / ${pool.max_hourly_send}`}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground">Capacity left</p>
                    <p className="font-semibold">
                      {formatNumber(pool.capacity_remaining ?? 0)}
                    </p>
                  </div>
                </div>
                <Link
                  href={`/account-pools/${pool.id}`}
                  className="mt-4 inline-block text-sm font-medium text-brand hover:underline"
                >
                  Manage accounts →
                </Link>
              </CardContent>
            </DataCard>
          ))}
        </div>
      )}
    </div>
  );
}
