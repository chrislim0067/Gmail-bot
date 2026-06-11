"use client";

import { Badge } from "@/components/ui/Badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/Table";
import { formatDateParts, formatSendDelay } from "@/lib/utils";
import type { SendJob, SendJobStatus } from "@/types/api";

function friendlyJobStatus(status: SendJobStatus): string {
  switch (status) {
    case "sent":
      return "Sent";
    case "pending":
      return "Waiting";
    case "locked":
      return "Sending…";
    case "failed":
      return "Failed";
    case "skipped":
      return "Skipped";
    default:
      return status.charAt(0).toUpperCase() + status.slice(1);
  }
}

function statusVariant(
  status: SendJobStatus
): "success" | "danger" | "warning" | "muted" {
  if (status === "sent") return "success";
  if (status === "failed") return "danger";
  if (status === "locked") return "warning";
  return "muted";
}

function DateTimeCell({ value }: { value?: string }) {
  const parts = formatDateParts(value);
  if (!parts) {
    return <span className="text-muted-foreground">—</span>;
  }
  return (
    <div className="tabular-nums">
      <div className="text-sm text-foreground">{parts.date}</div>
      <div className="text-xs text-muted-foreground">{parts.time}</div>
    </div>
  );
}

function PersonCell({
  name,
  email,
  leadId,
}: {
  name?: string;
  email?: string;
  leadId: string;
}) {
  const displayEmail = email ?? leadId;
  return (
    <div className="min-w-0 max-w-[220px]">
      {name ? (
        <>
          <div className="truncate font-medium text-foreground">{name}</div>
          <div className="truncate text-xs text-muted-foreground">
            {displayEmail}
          </div>
        </>
      ) : (
        <div className="truncate font-medium text-foreground">{displayEmail}</div>
      )}
    </div>
  );
}

interface SendHistoryTableProps {
  jobs: SendJob[];
}

export function SendHistoryTable({ jobs }: SendHistoryTableProps) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Person</TableHead>
          <TableHead>Subject</TableHead>
          <TableHead>Status</TableHead>
          <TableHead>Planned for</TableHead>
          <TableHead>Sent at</TableHead>
          <TableHead>Problem</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {jobs.map((job) => {
          const delay = formatSendDelay(job.scheduled_at, job.sent_at);
          return (
            <TableRow key={job.id}>
              <TableCell>
                <PersonCell
                  name={job.lead_name}
                  email={job.lead_email}
                  leadId={job.lead_id}
                />
              </TableCell>
              <TableCell className="max-w-[200px]">
                {job.subject ? (
                  <span
                    className="line-clamp-2 text-sm text-foreground"
                    title={job.subject}
                  >
                    {job.subject}
                  </span>
                ) : (
                  <span className="text-sm text-muted-foreground">—</span>
                )}
              </TableCell>
              <TableCell>
                <Badge variant={statusVariant(job.status)}>
                  {friendlyJobStatus(job.status)}
                </Badge>
              </TableCell>
              <TableCell>
                <DateTimeCell value={job.scheduled_at} />
              </TableCell>
              <TableCell>
                <DateTimeCell value={job.sent_at} />
                {delay && (
                  <div className="mt-0.5 text-xs text-muted-foreground">
                    {delay}
                  </div>
                )}
              </TableCell>
              <TableCell className="max-w-[180px]">
                {job.error_message ? (
                  <span
                    className="line-clamp-2 text-sm text-danger"
                    title={job.error_message}
                  >
                    {job.error_message}
                  </span>
                ) : (
                  <span className="text-sm text-muted-foreground">—</span>
                )}
              </TableCell>
            </TableRow>
          );
        })}
      </TableBody>
    </Table>
  );
}
