"use client";

import { useEffect, useState } from "react";
import { AlertTriangle, Shield } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Badge } from "@/components/ui/Badge";
import { Alert } from "@/components/ui/Alert";
import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";
import { PageLoader } from "@/components/ui/LoadingSpinner";
import { ProgressBar } from "@/components/ui/ProgressBar";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/Table";
import { riskApi } from "@/lib/api";
import { formatDate } from "@/lib/utils";
import type { RiskEvent, RiskOverview } from "@/types/api";

export default function RiskPage() {
  const [overview, setOverview] = useState<RiskOverview | null>(null);
  const [events, setEvents] = useState<RiskEvent[]>([]);
  const [notes, setNotes] = useState("");
  const [loading, setLoading] = useState(true);
  const [acknowledging, setAcknowledging] = useState(false);

  async function loadData() {
    setLoading(true);
    try {
      const [overviewData, eventsData] = await Promise.all([
        riskApi.overview(),
        riskApi.events({ page: 1 }),
      ]);
      setOverview(overviewData);
      setEvents(eventsData.items);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
  }, []);

  async function handleAcknowledge() {
    setAcknowledging(true);
    try {
      await riskApi.acknowledge({ acknowledge_all: true, notes });
      setNotes("");
      await loadData();
    } finally {
      setAcknowledging(false);
    }
  }

  const scorePercent = overview
    ? Math.min(100, (overview.global_risk_score / overview.threshold) * 100)
    : 0;

  const scoreVariant =
    scorePercent >= 100 ? "danger" : scorePercent >= 70 ? "warning" : "success";

  const scoreColor =
    scorePercent >= 100
      ? "text-danger"
      : scorePercent >= 70
        ? "text-warning"
        : "text-success";

  return (
    <div className="space-y-6">
      <PageHeader
        title="Risk Budget"
        description="Global risk score and event timeline"
      />

      {loading ? (
        <PageLoader />
      ) : (
        <>
          {overview?.review_required && (
            <Alert variant="danger" title="Risk review required" icon={AlertTriangle}>
              New campaign starts blocked. {overview.paused_campaigns} campaigns
              affected. Acknowledge events below to resume.
            </Alert>
          )}

          <div className="grid gap-6 lg:grid-cols-3">
            <Card className="lg:col-span-1">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Shield className="h-5 w-5 text-brand" />
                  Global risk score
                </CardTitle>
              </CardHeader>
              <CardContent className="text-center">
                <p className={`text-5xl font-semibold tabular-nums ${scoreColor}`}>
                  {overview?.global_risk_score ?? 0}
                </p>
                <p className="mt-1 text-sm text-muted-foreground">
                  Threshold: {overview?.threshold ?? 100}
                </p>
                <ProgressBar
                  className="mx-auto mt-4 max-w-xs"
                  value={overview?.global_risk_score ?? 0}
                  max={overview?.threshold ?? 100}
                  variant={scoreVariant}
                />
                <p className="mt-4 text-sm text-muted-foreground">
                  {overview?.recent_events_count ?? 0} recent events
                </p>
              </CardContent>
            </Card>

            <Card className="lg:col-span-2">
              <CardHeader>
                <CardTitle>Acknowledge risk events</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <Input
                  label="Notes"
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="Document your review decision"
                />
                <Button
                  onClick={handleAcknowledge}
                  loading={acknowledging}
                  disabled={!overview?.review_required}
                >
                  Acknowledge all events
                </Button>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Recent risk events</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              {events.length === 0 ? (
                <EmptyState
                  icon={Shield}
                  title="No risk events recorded"
                  description="Risk events will appear here when thresholds are approached."
                  compact
                />
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Type</TableHead>
                      <TableHead>Severity</TableHead>
                      <TableHead>Delta</TableHead>
                      <TableHead>Message</TableHead>
                      <TableHead>Date</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {events.map((event) => (
                      <TableRow key={event.id}>
                        <TableCell>{event.event_type}</TableCell>
                        <TableCell>
                          <Badge
                            variant={
                              event.severity === "high"
                                ? "danger"
                                : event.severity === "medium"
                                  ? "warning"
                                  : "default"
                            }
                          >
                            {event.severity}
                          </Badge>
                        </TableCell>
                        <TableCell>+{event.score_delta}</TableCell>
                        <TableCell className="text-muted-foreground">
                          {event.message}
                        </TableCell>
                        <TableCell className="text-muted-foreground">
                          {formatDate(event.created_at)}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
