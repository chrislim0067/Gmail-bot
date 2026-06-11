"use client";

import { useEffect, useRef, useState } from "react";
import { FileText, Plus, Type } from "lucide-react";
import { MessageTemplateList } from "@/components/templates/MessageTemplateList";
import { SubjectForm } from "@/components/templates/SubjectForm";
import { SubjectList } from "@/components/templates/SubjectList";
import { TemplateForm } from "@/components/templates/TemplateForm";
import {
  TextFileImport,
  type TextFileImportHandle,
} from "@/components/templates/TextFileImport";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { Card, CardContent } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";
import { PageLoader } from "@/components/ui/LoadingSpinner";
import { ApiClientError, subjectsApi, templatesApi } from "@/lib/api";
import type { EmailSubject, Template } from "@/types/api";
import { cn } from "@/lib/utils";

type Tab = "messages" | "subjects";

export default function TemplatesPage() {
  const [tab, setTab] = useState<Tab>("messages");
  const [templates, setTemplates] = useState<Template[]>([]);
  const [subjects, setSubjects] = useState<EmailSubject[]>([]);
  const [loading, setLoading] = useState(true);
  const [showMessageForm, setShowMessageForm] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const subjectImportRef = useRef<TextFileImportHandle>(null);

  function formatError(err: unknown, fallback: string): string {
    if (err instanceof ApiClientError) return err.message;
    if (err instanceof Error) return err.message;
    return fallback;
  }

  async function loadAll() {
    setLoading(true);
    try {
      const [templatesResult, subjectsResult] = await Promise.all([
        templatesApi.list({ limit: 100 }),
        subjectsApi.list(),
      ]);
      setTemplates(templatesResult.items);
      setSubjects(subjectsResult.items);
      setActionError(null);
    } catch (err) {
      setActionError(formatError(err, "Could not load outreach content."));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadAll();
  }, []);

  async function handleCreateMessage(data: {
    name: string;
    html_template: string;
    text_template: string;
  }) {
    setSubmitting(true);
    setActionError(null);
    try {
      await templatesApi.create(data);
      setShowMessageForm(false);
      await loadAll();
    } catch (err) {
      setActionError(formatError(err, "Could not save message template."));
    } finally {
      setSubmitting(false);
    }
  }

  async function handleCreateSubject(text: string) {
    setSubmitting(true);
    setActionError(null);
    try {
      await subjectsApi.create({ text });
      await loadAll();
    } catch (err) {
      setActionError(formatError(err, "Could not save subject line."));
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDeleteTemplate(id: string) {
    setDeleting(true);
    setActionError(null);
    try {
      await templatesApi.delete(id);
      await loadAll();
    } catch (err) {
      setActionError(formatError(err, "Could not remove message template."));
    } finally {
      setDeleting(false);
    }
  }

  async function handleDeleteAllTemplates() {
    setDeleting(true);
    setActionError(null);
    try {
      await templatesApi.deleteAll();
      await loadAll();
    } catch (err) {
      setActionError(formatError(err, "Could not remove all message templates."));
    } finally {
      setDeleting(false);
    }
  }

  async function handleDeleteSubject(id: string) {
    setDeleting(true);
    setActionError(null);
    try {
      await subjectsApi.delete(id);
      await loadAll();
    } catch (err) {
      setActionError(formatError(err, "Could not remove subject line."));
    } finally {
      setDeleting(false);
    }
  }

  async function handleDeleteAllSubjects() {
    setDeleting(true);
    setActionError(null);
    try {
      await subjectsApi.deleteAll();
      await loadAll();
    } catch (err) {
      setActionError(formatError(err, "Could not remove all subject lines."));
    } finally {
      setDeleting(false);
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Outreach content"
        description="Message templates and subject lines. Each candidate gets a random pair plus Thanks, Chris."
        actions={
          tab === "messages" && !showMessageForm ? (
            <Button size="sm" onClick={() => setShowMessageForm(true)}>
              <Plus className="h-4 w-4" />
              New message
            </Button>
          ) : undefined
        }
      />

      <div className="flex gap-2 rounded-2xl border border-border bg-white/80 p-1 shadow-soft">
        <button
          type="button"
          onClick={() => setTab("messages")}
          className={cn(
            "flex flex-1 items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-medium transition-colors",
            tab === "messages"
              ? "bg-violet-600 text-white shadow-sm"
              : "text-muted-foreground hover:bg-stone-50"
          )}
        >
          <FileText className="h-4 w-4" />
          Messages ({templates.length})
        </button>
        <button
          type="button"
          onClick={() => setTab("subjects")}
          className={cn(
            "flex flex-1 items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-medium transition-colors",
            tab === "subjects"
              ? "bg-violet-600 text-white shadow-sm"
              : "text-muted-foreground hover:bg-stone-50"
          )}
        >
          <Type className="h-4 w-4" />
          Subjects ({subjects.length})
        </button>
      </div>

      {actionError && (
        <Alert variant="danger" onDismiss={() => setActionError(null)}>
          {actionError}
          {actionError.includes("API server") && (
            <span className="mt-2 block text-xs">
              Restart <strong>GmailOutreach-Start.bat</strong> from the project
              folder, then try again.
            </span>
          )}
        </Alert>
      )}

      {loading ? (
        <PageLoader />
      ) : tab === "messages" ? (
        <div className="space-y-6">
          <TextFileImport
            label="Import from text file"
            hint="Plain text only. Separate templates with --- or --- Template name ---."
            sampleFileHint="Sample file: Sourse/Templates.txt in the project folder."
            example={`--- Version 1 ---
Hi {{name}},

Your message here...

--- Version 2 ---
Hi {{name}},

Another message...`}
            onImport={(file) => templatesApi.importText(file)}
            onComplete={loadAll}
            defaultOpen={templates.length === 0}
          />

          {showMessageForm && (
            <TemplateForm
              onSubmit={handleCreateMessage}
              onCancel={() => setShowMessageForm(false)}
              submitting={submitting}
            />
          )}

          {templates.length === 0 && !showMessageForm ? (
            <Card>
              <CardContent>
                <EmptyState
                  icon={FileText}
                  title="No message templates yet"
                  description="Import Templates.txt or add a message manually."
                  action={
                    <Button size="sm" onClick={() => setShowMessageForm(true)}>
                      <Plus className="h-4 w-4" />
                      New message
                    </Button>
                  }
                />
              </CardContent>
            </Card>
          ) : (
            templates.length > 0 && (
              <MessageTemplateList
                templates={templates}
                onDelete={handleDeleteTemplate}
                onDeleteAll={handleDeleteAllTemplates}
                deleting={deleting}
              />
            )
          )}
        </div>
      ) : (
        <div className="space-y-6">
          <TextFileImport
            ref={subjectImportRef}
            label="Import subjects from text file"
            hint="One subject per line. Lines starting with # are ignored."
            sampleFileHint="Sample file: Sourse/Subjects.txt in the project folder."
            example={`Quick question for {{name}}
Following up, {{name}}`}
            onImport={(file) => subjectsApi.importText(file)}
            onComplete={loadAll}
            defaultOpen={subjects.length === 0}
          />

          <Card>
            <CardContent className="pt-6">
              <SubjectForm
                onSubmit={handleCreateSubject}
                submitting={submitting}
              />
            </CardContent>
          </Card>

          <SubjectList
            subjects={subjects}
            onDelete={handleDeleteSubject}
            onDeleteAll={handleDeleteAllSubjects}
            onImportFromFile={() => subjectImportRef.current?.openFilePicker()}
            deleting={deleting}
          />
        </div>
      )}
    </div>
  );
}
