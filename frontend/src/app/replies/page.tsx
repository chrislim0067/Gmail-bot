"use client";

import { useEffect, useState } from "react";
import { MessageSquare, RefreshCw } from "lucide-react";
import { ReplyCard } from "@/components/replies/ReplyCard";
import { Button } from "@/components/ui/Button";
import { Card, CardContent } from "@/components/ui/Card";
import { Alert } from "@/components/ui/Alert";
import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";
import { PageLoader } from "@/components/ui/LoadingSpinner";
import { gmailApi, repliesApi } from "@/lib/api";
import type { GmailAccount, Reply } from "@/types/api";

export default function RepliesPage() {
  const [replies, setReplies] = useState<Reply[]>([]);
  const [accounts, setAccounts] = useState<GmailAccount[]>([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState<string | null>(null);
  const [syncMessage, setSyncMessage] = useState<string | null>(null);
  const [syncError, setSyncError] = useState<string | null>(null);

  async function loadReplies() {
    setLoading(true);
    try {
      const [replyData, accountData] = await Promise.all([
        repliesApi.list({ page: 1 }),
        gmailApi.listAccounts(),
      ]);
      setReplies(replyData.items);
      setAccounts(accountData.items);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadReplies();
  }, []);

  async function syncAccount(accountId: string, accountEmail: string) {
    setSyncing(accountId);
    setSyncMessage(null);
    setSyncError(null);
    try {
      const result = await gmailApi.syncReplies(accountId);
      if (result.reason === "mock_no_replies") {
        setSyncMessage(
          "Mock mode is enabled — connect a real Gmail account to sync replies."
        );
      } else if (result.new_replies > 0) {
        setSyncMessage(
          `Found ${result.new_replies} new ${result.new_replies === 1 ? "reply" : "replies"}.`
        );
      } else {
        setSyncMessage(
          `Synced ${accountEmail}: scanned ${result.messages_scanned} inbox messages, no new replies matched your sent emails.`
        );
      }
      await loadReplies();
    } catch (err) {
      setSyncError(
        err instanceof Error ? err.message : "Failed to sync replies from Gmail."
      );
    } finally {
      setSyncing(null);
    }
  }

  async function syncAllAccounts() {
    if (accounts.length === 0) return;
    setSyncMessage(null);
    setSyncError(null);
    let totalNew = 0;
    for (const account of accounts) {
      setSyncing(account.id);
      try {
        const result = await gmailApi.syncReplies(account.id);
        totalNew += result.new_replies;
      } catch (err) {
        setSyncError(
          err instanceof Error
            ? `${account.email}: ${err.message}`
            : `Failed to sync ${account.email}.`
        );
        setSyncing(null);
        return;
      }
    }
    setSyncing(null);
    setSyncMessage(
      totalNew > 0
        ? `Synced all ${accounts.length} accounts — found ${totalNew} new ${totalNew === 1 ? "reply" : "replies"}.`
        : `Synced all ${accounts.length} accounts — no new replies matched your sent emails.`
    );
    await loadReplies();
  }

  function accountLabel(email: string) {
    return email.split("@")[0];
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Replies"
        description={`Inbound replies synced from connected Gmail accounts${
          accounts.length > 0
            ? ` · ${accounts.length} connected ${accounts.length === 1 ? "account" : "accounts"}`
            : ""
        }`}
        actions={
          accounts.length > 0 ? (
            <div className="flex max-w-xl flex-wrap justify-end gap-2">
              {accounts.length > 1 && (
                <Button
                  variant="secondary"
                  size="sm"
                  loading={syncing !== null}
                  onClick={syncAllAccounts}
                >
                  <RefreshCw className="h-4 w-4" />
                  Sync all ({accounts.length})
                </Button>
              )}
              {accounts.map((account) => (
                <Button
                  key={account.id}
                  variant="outline"
                  size="sm"
                  loading={syncing === account.id}
                  disabled={syncing !== null && syncing !== account.id}
                  onClick={() => syncAccount(account.id, account.email)}
                >
                  <RefreshCw className="h-4 w-4" />
                  Sync {accountLabel(account.email)}
                </Button>
              ))}
            </div>
          ) : undefined
        }
      />

      {syncMessage && (
        <Alert variant="info" onDismiss={() => setSyncMessage(null)}>
          {syncMessage}
        </Alert>
      )}
      {syncError && (
        <Alert variant="danger" onDismiss={() => setSyncError(null)}>
          {syncError}
        </Alert>
      )}

      {loading ? (
        <PageLoader />
      ) : replies.length === 0 ? (
        <Card>
          <CardContent>
            <EmptyState
              icon={MessageSquare}
              title="No replies yet"
              description="After you send campaign emails, click Sync on a connected Gmail account to fetch replies that match your sent messages."
            />
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {replies.map((reply) => (
            <ReplyCard key={reply.id} reply={reply} />
          ))}
        </div>
      )}
    </div>
  );
}
