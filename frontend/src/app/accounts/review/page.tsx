"use client";

import { useEffect, useState } from "react";
import { Check, ClipboardCheck, X } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { TierBadge } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";
import { PageLoader } from "@/components/ui/LoadingSpinner";
import { gmailApi } from "@/lib/api";
import type { AccountTier, GmailAccount } from "@/types/api";

export default function AccountReviewPage() {
  const [accounts, setAccounts] = useState<GmailAccount[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [notes, setNotes] = useState("");
  const [newTier, setNewTier] = useState<AccountTier>("warming");
  const [submitting, setSubmitting] = useState(false);

  async function loadAccounts() {
    setLoading(true);
    try {
      const data = await gmailApi.listAccounts();
      setAccounts(data.items.filter((a) => a.review_required));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadAccounts();
  }, []);

  async function handleReview(approved: boolean) {
    if (!selectedId) return;
    setSubmitting(true);
    try {
      await gmailApi.reviewAccount(selectedId, {
        approved,
        notes,
        new_tier: approved ? newTier : undefined,
      });
      setSelectedId(null);
      setNotes("");
      await loadAccounts();
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Account Review Queue"
        description="Approve or reject restricted accounts before sending resumes"
      />

      {loading ? (
        <PageLoader />
      ) : accounts.length === 0 ? (
        <Card>
          <CardContent>
            <EmptyState
              icon={ClipboardCheck}
              title="No accounts pending review"
              description="All connected accounts have been reviewed and approved."
            />
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 lg:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>Pending review ({accounts.length})</CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="divide-y divide-border-subtle">
                {accounts.map((account) => (
                  <li key={account.id}>
                    <button
                      type="button"
                      onClick={() => setSelectedId(account.id)}
                      className={`flex w-full items-center justify-between py-3 text-left transition-colors ${
                        selectedId === account.id
                          ? "text-brand"
                          : "text-foreground"
                      }`}
                    >
                      <div>
                        <p className="font-medium">{account.email}</p>
                        <div className="mt-1 flex gap-2">
                          <TierBadge tier={account.account_tier} />
                          <span className="text-xs text-muted-foreground">
                            Score {account.health_score}
                          </span>
                        </div>
                      </div>
                    </button>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>

          {selectedId && (
            <Card>
              <CardHeader>
                <CardTitle>Review decision</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <Input
                  label="Notes"
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="Reason for approval or rejection"
                />
                <Select
                  label="New tier (if approved)"
                  value={newTier}
                  onChange={(e) => setNewTier(e.target.value as AccountTier)}
                >
                  <option value="new">new</option>
                  <option value="warming">warming</option>
                  <option value="stable">stable</option>
                  <option value="trusted">trusted</option>
                </Select>
                <div className="flex gap-2">
                  <Button
                    className="flex-1"
                    loading={submitting}
                    onClick={() => handleReview(true)}
                  >
                    <Check className="h-4 w-4" />
                    Approve
                  </Button>
                  <Button
                    variant="danger"
                    className="flex-1"
                    loading={submitting}
                    onClick={() => handleReview(false)}
                  >
                    <X className="h-4 w-4" />
                    Reject
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      )}
    </div>
  );
}
