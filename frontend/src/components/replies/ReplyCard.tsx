"use client";

import { useState } from "react";
import { ChevronDown, ChevronUp, Mail } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { DataCard, CardContent } from "@/components/ui/Card";
import { formatDate } from "@/lib/utils";
import {
  initials,
  parseFromHeader,
  parseReplySnippet,
} from "@/lib/replyFormat";
import type { Reply } from "@/types/api";

interface ReplyCardProps {
  reply: Reply;
}

export function ReplyCard({ reply }: ReplyCardProps) {
  const [showQuoted, setShowQuoted] = useState(false);
  const sender = parseFromHeader(reply.from_email ?? reply.lead_email ?? "");
  const parsed = reply.snippet ? parseReplySnippet(reply.snippet) : null;
  const displayName = sender.name ?? sender.email.split("@")[0];

  return (
    <DataCard className="overflow-hidden">
      <CardContent className="p-0">
        <div className="flex gap-4 p-5 sm:p-6">
          <div
            className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-violet-500 to-pink-500 text-sm font-bold text-white shadow-md shadow-violet-500/20 ring-2 ring-white"
            aria-hidden
          >
            {initials(sender.name, sender.email)}
          </div>

          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <h3 className="truncate text-base font-semibold text-foreground">
                    {displayName}
                  </h3>
                  {reply.campaign_name && (
                    <Badge variant="info">{reply.campaign_name}</Badge>
                  )}
                </div>
                <p className="mt-0.5 truncate text-sm text-muted-foreground">
                  {sender.email}
                </p>
                <p className="mt-1 text-sm font-medium text-foreground">
                  {reply.subject ?? "(No subject)"}
                </p>
              </div>
              <time className="shrink-0 text-xs text-muted-foreground">
                {formatDate(reply.received_at)}
              </time>
            </div>

            {parsed?.body ? (
              <div className="mt-4 rounded-2xl border border-border-subtle bg-gradient-to-br from-stone-50 to-violet-50/30 px-4 py-3">
                <p className="whitespace-pre-wrap text-sm leading-relaxed text-foreground">
                  {parsed.body}
                </p>
              </div>
            ) : (
              <p className="mt-4 text-sm italic text-muted-foreground">No preview text</p>
            )}

            {parsed?.quoted && (
              <div className="mt-3">
                <button
                  type="button"
                  onClick={() => setShowQuoted((v) => !v)}
                  className="inline-flex items-center gap-1.5 text-xs font-medium text-muted-foreground transition-colors hover:text-foreground"
                >
                  {showQuoted ? (
                    <ChevronUp className="h-3.5 w-3.5" />
                  ) : (
                    <ChevronDown className="h-3.5 w-3.5" />
                  )}
                  {showQuoted ? "Hide" : "Show"} quoted message
                </button>
                {showQuoted && (
                  <div className="mt-2 rounded-xl border border-dashed border-border bg-surface px-4 py-3">
                    {parsed.quoteHeader && (
                      <p className="mb-2 text-xs text-muted-foreground">
                        {parsed.quoteHeader}
                      </p>
                    )}
                    <p className="whitespace-pre-wrap text-xs leading-relaxed text-muted-foreground">
                      {parsed.quoted}
                    </p>
                  </div>
                )}
              </div>
            )}

            {reply.lead_email && (
              <div className="mt-4 flex items-center gap-1.5 text-xs text-muted-foreground">
                <Mail className="h-3.5 w-3.5" />
                <span>
                  Reply to lead{" "}
                  <span className="font-medium text-foreground">{reply.lead_email}</span>
                </span>
              </div>
            )}
          </div>
        </div>
      </CardContent>
    </DataCard>
  );
}
