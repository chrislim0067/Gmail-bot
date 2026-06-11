"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft, Plus, Upload, Users } from "lucide-react";
import { Alert } from "@/components/ui/Alert";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { Input } from "@/components/ui/Input";
import { PageLoader } from "@/components/ui/LoadingSpinner";
import { PageHeader } from "@/components/ui/PageHeader";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/Table";
import { ApiClientError, campaignsApi } from "@/lib/api";
import type { Lead, LeadImportStatus } from "@/types/api";

function ComplianceCheckbox({
  checked,
  onChange,
  children,
}: {
  checked: boolean;
  onChange: (v: boolean) => void;
  children: React.ReactNode;
}) {
  return (
    <label className="flex items-start gap-3 rounded-2xl border border-border-subtle bg-gradient-to-br from-stone-50 to-violet-50/20 p-4 transition-all hover:border-violet-100">
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="mt-0.5 h-4 w-4 rounded border-border text-brand focus:ring-brand/20"
      />
      <span className="text-sm leading-relaxed text-foreground">{children}</span>
    </label>
  );
}

export default function CampaignLeadsPage() {
  const params = useParams();
  const campaignId = params.id as string;
  const fileRef = useRef<HTMLInputElement>(null);

  const [leads, setLeads] = useState<Lead[]>([]);
  const [loading, setLoading] = useState(true);
  const [complianceAck, setComplianceAck] = useState(false);
  const [sourceLabel, setSourceLabel] = useState("");
  const [allowRoleBased, setAllowRoleBased] = useState(false);
  const [importing, setImporting] = useState(false);
  const [importStatus, setImportStatus] = useState<LeadImportStatus | null>(null);
  const [importSuccess, setImportSuccess] = useState("");
  const [error, setError] = useState("");
  const [manualEmail, setManualEmail] = useState("");
  const [manualFirstName, setManualFirstName] = useState("");
  const [manualLastName, setManualLastName] = useState("");
  const [manualCompany, setManualCompany] = useState("");
  const [manualSource, setManualSource] = useState("");
  const [manualComplianceAck, setManualComplianceAck] = useState(false);
  const [manualAllowRoleBased, setManualAllowRoleBased] = useState(false);
  const [addingLead, setAddingLead] = useState(false);
  const [manualSuccess, setManualSuccess] = useState("");

  async function loadLeads() {
    setLoading(true);
    try {
      const data = await campaignsApi.listLeads(campaignId, { limit: 100 });
      setLeads(data?.items ?? []);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadLeads();
  }, [campaignId]);

  async function handleImport(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setImportSuccess("");

    if (!complianceAck) {
      setError("Check the compliance box before importing.");
      return;
    }

    const file = fileRef.current?.files?.[0];
    if (!file) {
      setError("Please select a CSV file.");
      return;
    }

    setImporting(true);
    setImportStatus(null);

    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("compliance_acknowledged", "true");
      if (sourceLabel) formData.append("source_label", sourceLabel);
      if (allowRoleBased) formData.append("allow_role_based_emails", "true");

      const result = await campaignsApi.importLeads(campaignId, formData);
      setImportStatus({
        status: result.status,
        imported: result.imported,
        skipped: result.skipped,
        invalid: result.invalid,
        errors: result.errors ?? [],
      });

      if (result.imported > 0) {
        setImportSuccess(
          `Imported ${result.imported} lead${result.imported === 1 ? "" : "s"}.`
        );
      } else if (result.skipped > 0) {
        setError(
          `No new leads added. ${result.skipped} row${
            result.skipped === 1 ? " was" : "s were"
          } skipped — they may already be in this campaign.`
        );
      }

      await loadLeads();
      if (fileRef.current) fileRef.current.value = "";
    } catch (err) {
      setError(
        err instanceof ApiClientError
          ? err.message
          : err instanceof Error
            ? err.message
            : "Import failed"
      );
    } finally {
      setImporting(false);
    }
  }

  async function handleAddLead(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setManualSuccess("");

    if (!manualComplianceAck) {
      setError("You must acknowledge compliance requirements before adding a lead.");
      return;
    }

    setAddingLead(true);
    try {
      const emailAdded = manualEmail;
      await campaignsApi.createLead(campaignId, {
        email: emailAdded,
        first_name: manualFirstName || undefined,
        last_name: manualLastName || undefined,
        company: manualCompany || undefined,
        source: manualSource || undefined,
        compliance_acknowledged: true,
        allow_role_based_emails: manualAllowRoleBased,
      });
      setManualEmail("");
      setManualFirstName("");
      setManualLastName("");
      setManualCompany("");
      setManualSuccess(`Added ${emailAdded}`);
      await loadLeads();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to add lead");
    } finally {
      setAddingLead(false);
    }
  }

  return (
    <div className="space-y-6">
      <Link
        href={`/campaigns/${campaignId}`}
        className="inline-flex items-center gap-1.5 text-sm text-muted-foreground transition-colors hover:text-brand"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to campaign
      </Link>

      <PageHeader
        title="Campaign leads"
        description="Add leads one at a time or import a CSV file. All leads require compliance acknowledgement."
      />

      {error && <Alert variant="danger">{error}</Alert>}
      {importSuccess && <Alert variant="success">{importSuccess}</Alert>}
      {manualSuccess && <Alert variant="success">{manualSuccess}</Alert>}

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Add lead manually</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleAddLead} className="space-y-4">
              <Input
                label="Email"
                type="email"
                value={manualEmail}
                onChange={(e) => setManualEmail(e.target.value)}
                required
              />
              <div className="grid gap-4 sm:grid-cols-2">
                <Input
                  label="First name"
                  value={manualFirstName}
                  onChange={(e) => setManualFirstName(e.target.value)}
                />
                <Input
                  label="Last name"
                  value={manualLastName}
                  onChange={(e) => setManualLastName(e.target.value)}
                />
              </div>
              <Input
                label="Company"
                value={manualCompany}
                onChange={(e) => setManualCompany(e.target.value)}
              />
              <Input
                label="Source"
                value={manualSource}
                onChange={(e) => setManualSource(e.target.value)}
                hint="Where did this lead come from?"
              />

              <ComplianceCheckbox
                checked={manualComplianceAck}
                onChange={setManualComplianceAck}
              >
                <strong>Compliance acknowledgement (required):</strong> I confirm
                this lead was obtained lawfully and I will honor unsubscribe
                requests.
              </ComplianceCheckbox>

              <label className="flex items-center gap-2 text-sm text-muted-foreground">
                <input
                  type="checkbox"
                  checked={manualAllowRoleBased}
                  onChange={(e) => setManualAllowRoleBased(e.target.checked)}
                  className="h-4 w-4 rounded border-border text-brand focus:ring-brand/20"
                />
                Allow role-based emails (info@, sales@, etc.)
              </label>

              <Button type="submit" loading={addingLead} disabled={!manualComplianceAck}>
                <Plus className="h-4 w-4" />
                Add lead
              </Button>
            </form>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Import leads</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleImport} className="space-y-4">
              <div>
                <label className="mb-1.5 block text-sm font-medium text-foreground">
                  CSV file
                </label>
                <input
                  ref={fileRef}
                  type="file"
                  accept=".csv"
                  className="block w-full text-sm text-muted-foreground file:mr-4 file:rounded-lg file:border-0 file:bg-brand-muted file:px-4 file:py-2 file:text-sm file:font-medium file:text-brand hover:file:bg-brand-subtle"
                />
                <p className="mt-1.5 text-xs text-muted-foreground">
                  Required: <strong>email</strong>. Use <strong>name</strong> or{" "}
                  <strong>first_name</strong> for personalization. Optional: last_name, company
                </p>
              </div>

              <Input
                label="Source label"
                value={sourceLabel}
                onChange={(e) => setSourceLabel(e.target.value)}
                hint="Where did these leads come from? (recommended for cold outreach)"
              />

              <ComplianceCheckbox checked={complianceAck} onChange={setComplianceAck}>
                <strong>Compliance acknowledgement (required):</strong> I confirm
                these leads were obtained lawfully, I have a valid basis for
                outreach, and I will honor unsubscribe requests. I understand
                role-based emails (info@, support@, etc.) are blocked unless
                explicitly allowed below.
              </ComplianceCheckbox>

              <label className="flex items-center gap-2 text-sm text-muted-foreground">
                <input
                  type="checkbox"
                  checked={allowRoleBased}
                  onChange={(e) => setAllowRoleBased(e.target.checked)}
                  className="h-4 w-4 rounded border-border text-brand focus:ring-brand/20"
                />
                Allow role-based emails (info@, sales@, etc.)
              </label>

              <Button type="submit" loading={importing} disabled={!complianceAck}>
                <Upload className="h-4 w-4" />
                Upload & import
              </Button>
            </form>

            {importStatus && (
              <Alert
                variant={importStatus.imported > 0 ? "success" : "info"}
                title={
                  importStatus.imported > 0
                    ? "Import complete"
                    : importStatus.skipped > 0
                      ? "No new leads"
                      : `Import ${importStatus.status}`
                }
                className="mt-4"
              >
                Imported: {importStatus.imported} · Skipped: {importStatus.skipped}
                {(importStatus.invalid ?? 0) > 0 &&
                  ` · Invalid: ${importStatus.invalid}`}
                {importStatus.errors.length > 0 && (
                  <ul className="mt-2 list-inside list-disc text-sm">
                    {importStatus.errors.slice(0, 5).map((err, i) => (
                      <li key={i}>{err}</li>
                    ))}
                  </ul>
                )}
              </Alert>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Leads ({leads.length})</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {loading ? (
            <PageLoader />
          ) : leads.length === 0 ? (
            <EmptyState
              compact
              icon={Users}
              title="No leads yet"
              description="Add a lead manually or import a CSV to get started."
            />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Email</TableHead>
                  <TableHead>Name</TableHead>
                  <TableHead>Company</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {leads.map((lead) => (
                  <TableRow key={lead.id}>
                    <TableCell className="font-medium">{lead.email}</TableCell>
                    <TableCell className="text-muted-foreground">
                      {[lead.first_name, lead.last_name].filter(Boolean).join(" ") ||
                        "—"}
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {lead.company ?? "—"}
                    </TableCell>
                    <TableCell>
                      <Badge variant="muted">{lead.status}</Badge>
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
