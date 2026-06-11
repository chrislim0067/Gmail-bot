"use client";

import { useMemo, useState } from "react";
import { ChevronDown, ChevronUp, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import {
  sortTemplateNames,
  templateToReadableBody,
} from "@/lib/template-builder";
import type { Template } from "@/types/api";
import { cn } from "@/lib/utils";

interface MessageTemplateListProps {
  templates: Template[];
  onDelete: (id: string) => Promise<void>;
  onDeleteAll: () => Promise<void>;
  deleting?: boolean;
}

function splitPreview(body: string): { headline: string; rest: string } {
  const lines = body.split("\n").map((line) => line.trim()).filter(Boolean);
  return {
    headline: lines[0] ?? "",
    rest: lines.slice(1).join("\n"),
  };
}

export function MessageTemplateList({
  templates,
  onDelete,
  onDeleteAll,
  deleting = false,
}: MessageTemplateListProps) {
  const [search, setSearch] = useState("");
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const sorted = useMemo(
    () => [...templates].sort((a, b) => sortTemplateNames(a.name, b.name)),
    [templates]
  );

  const filtered = useMemo(() => {
    const query = search.trim().toLowerCase();
    if (!query) return sorted;
    return sorted.filter((template) => {
      const body = templateToReadableBody(template).toLowerCase();
      return (
        template.name.toLowerCase().includes(query) || body.includes(query)
      );
    });
  }, [sorted, search]);

  async function handleDeleteAll() {
    if (
      !window.confirm(
        `Remove all ${templates.length} message templates? This cannot be undone.`
      )
    ) {
      return;
    }
    try {
      await onDeleteAll();
    } catch {
      /* Parent shows the error banner */
    }
  }

  async function handleDeleteOne(id: string, name: string) {
    if (!window.confirm(`Remove "${name}"?`)) return;
    try {
      await onDelete(id);
      if (expandedId === id) setExpandedId(null);
    } catch {
      /* Parent shows the error banner */
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-lg font-semibold text-foreground">
            Your messages
          </h2>
          <p className="text-sm text-muted-foreground">
            {templates.length} template{templates.length === 1 ? "" : "s"} ready
            for random selection
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={handleDeleteAll}
          loading={deleting}
          className="border-red-200 text-red-700 hover:bg-red-50"
        >
          <Trash2 className="h-4 w-4" />
          Remove all
        </Button>
      </div>

      <Input
        label="Search messages"
        placeholder="Search by version name or text..."
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        className="max-w-md"
      />

      {filtered.length === 0 ? (
        <p className="rounded-xl border border-dashed border-border px-4 py-8 text-center text-sm text-muted-foreground">
          No messages match your search.
        </p>
      ) : (
        <ul className="divide-y divide-border overflow-hidden rounded-2xl border border-border bg-white shadow-soft">
          {filtered.map((template) => {
            const body = templateToReadableBody(template);
            const { headline, rest } = splitPreview(body);
            const isExpanded = expandedId === template.id;

            return (
              <li key={template.id} className="bg-white">
                <div className="flex items-start gap-3 px-4 py-4 sm:px-5">
                  <span className="mt-0.5 shrink-0 rounded-lg bg-violet-100 px-2.5 py-1 text-xs font-semibold text-violet-800">
                    {template.name}
                  </span>

                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium text-foreground">
                      {headline || "Empty message"}
                    </p>
                    {!isExpanded && rest && (
                      <p className="mt-1 line-clamp-3 text-sm leading-relaxed text-muted-foreground">
                        {rest}
                      </p>
                    )}
                    {isExpanded && (
                      <pre className="mt-3 whitespace-pre-wrap rounded-xl bg-stone-50 px-4 py-3 text-sm leading-relaxed text-foreground">
                        {body}
                      </pre>
                    )}
                  </div>

                  <div className="flex shrink-0 flex-col gap-1 sm:flex-row">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() =>
                        setExpandedId(isExpanded ? null : template.id)
                      }
                      aria-expanded={isExpanded}
                    >
                      {isExpanded ? (
                        <>
                          <ChevronUp className="h-4 w-4" />
                          Hide
                        </>
                      ) : (
                        <>
                          <ChevronDown className="h-4 w-4" />
                          View full
                        </>
                      )}
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleDeleteOne(template.id, template.name)}
                      className={cn("text-red-600 hover:bg-red-50 hover:text-red-700")}
                    >
                      <Trash2 className="h-4 w-4" />
                      Remove
                    </Button>
                  </div>
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
