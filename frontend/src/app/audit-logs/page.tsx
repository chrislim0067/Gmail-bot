"use client";

import { useEffect, useState } from "react";
import { ScrollText } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Badge } from "@/components/ui/Badge";
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
import { auditApi } from "@/lib/api";
import { formatDate } from "@/lib/utils";
import type { AuditLogEntry } from "@/types/api";

export default function AuditLogsPage() {
  const [logs, setLogs] = useState<AuditLogEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionFilter, setActionFilter] = useState("");
  const [resourceFilter, setResourceFilter] = useState("");

  async function loadLogs() {
    setLoading(true);
    try {
      const data = await auditApi.list({
        action: actionFilter || undefined,
        resource_type: resourceFilter || undefined,
        page: 1,
      });
      setLogs(data.items);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadLogs();
  }, []);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Audit Logs"
        description="Append-only trail of sends, pauses, tier changes, and token events"
      />

      <Card>
        <CardHeader>
          <CardTitle>Filters</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap items-end gap-4">
            <Input
              label="Action"
              value={actionFilter}
              onChange={(e) => setActionFilter(e.target.value)}
              placeholder="e.g. campaign.start"
              className="max-w-xs"
            />
            <Input
              label="Resource type"
              value={resourceFilter}
              onChange={(e) => setResourceFilter(e.target.value)}
              placeholder="e.g. gmail_account"
              className="max-w-xs"
            />
            <Button size="sm" onClick={loadLogs}>
              Apply filters
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Events ({logs.length})</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {loading ? (
            <PageLoader />
          ) : logs.length === 0 ? (
            <EmptyState
              icon={ScrollText}
              title="No audit log entries found"
              description="Try adjusting your filters or check back after activity occurs."
              compact
            />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Action</TableHead>
                  <TableHead>Resource</TableHead>
                  <TableHead>Resource ID</TableHead>
                  <TableHead>Timestamp</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {logs.map((log) => (
                  <TableRow key={log.id}>
                    <TableCell>
                      <Badge variant="info">{log.action}</Badge>
                    </TableCell>
                    <TableCell className="capitalize">
                      {log.resource_type.replace(/_/g, " ")}
                    </TableCell>
                    <TableCell className="font-mono text-xs text-muted-foreground">
                      {log.resource_id ?? "—"}
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {formatDate(log.created_at)}
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
