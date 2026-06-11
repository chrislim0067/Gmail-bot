"use client";

import { useEffect, useState } from "react";
import { Plus, Trash2, UserMinus } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";
import { PageLoader } from "@/components/ui/LoadingSpinner";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/Table";
import { unsubscribesApi } from "@/lib/api";
import { formatDate } from "@/lib/utils";
import type { UnsubscribeEntry } from "@/types/api";

export default function UnsubscribesPage() {
  const [entries, setEntries] = useState<UnsubscribeEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [email, setEmail] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [removingId, setRemovingId] = useState<string | null>(null);

  async function loadEntries() {
    setLoading(true);
    try {
      const data = await unsubscribesApi.list({ page: 1 });
      setEntries(data.items);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadEntries();
  }, []);

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    try {
      await unsubscribesApi.addManual(email);
      setEmail("");
      await loadEntries();
    } finally {
      setSubmitting(false);
    }
  }

  async function handleRemove(entry: UnsubscribeEntry) {
    const confirmed = window.confirm(
      `Remove ${entry.email} from the suppression list? They may receive emails again.`
    );
    if (!confirmed) return;

    setRemovingId(entry.id);
    try {
      await unsubscribesApi.remove(entry.id);
      await loadEntries();
    } finally {
      setRemovingId(null);
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Unsubscribes"
        description="Global suppression list — bounced and unsubscribed addresses"
      />

      <Card>
        <CardHeader>
          <CardTitle>Manually add suppression</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleAdd} className="flex flex-wrap items-end gap-3">
            <Input
              type="email"
              placeholder="email@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="max-w-sm flex-1"
            />
            <Button type="submit" loading={submitting}>
              <Plus className="h-4 w-4" />
              Add to list
            </Button>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Suppression list ({entries.length})</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {loading ? (
            <PageLoader />
          ) : entries.length === 0 ? (
            <EmptyState
              icon={UserMinus}
              title="No suppressed addresses"
              description="Addresses that unsubscribe or bounce will appear here automatically."
              compact
            />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Email</TableHead>
                  <TableHead>Source</TableHead>
                  <TableHead>Added</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {entries.map((entry) => (
                  <TableRow key={entry.id}>
                    <TableCell className="font-medium">{entry.email}</TableCell>
                    <TableCell className="capitalize">{entry.source}</TableCell>
                    <TableCell className="text-muted-foreground">
                      {formatDate(entry.unsubscribed_at ?? entry.created_at)}
                    </TableCell>
                    <TableCell className="text-right">
                      <Button
                        variant="outline"
                        size="sm"
                        loading={removingId === entry.id}
                        onClick={() => handleRemove(entry)}
                      >
                        <Trash2 className="h-4 w-4" />
                        Remove
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
