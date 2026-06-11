"use client";

import { useMemo, useState } from "react";
import { Trash2, Upload } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import type { EmailSubject } from "@/types/api";

interface SubjectListProps {
  subjects: EmailSubject[];
  onDelete: (id: string) => Promise<void>;
  onDeleteAll: () => Promise<void>;
  onImportFromFile?: () => void;
  deleting?: boolean;
}

export function SubjectList({
  subjects,
  onDelete,
  onDeleteAll,
  onImportFromFile,
  deleting = false,
}: SubjectListProps) {
  const [search, setSearch] = useState("");

  const filtered = useMemo(() => {
    const query = search.trim().toLowerCase();
    if (!query) return subjects;
    return subjects.filter((s) => s.text.toLowerCase().includes(query));
  }, [subjects, search]);

  async function handleDeleteAll() {
    if (
      !window.confirm(
        `Remove all ${subjects.length} subject lines? This cannot be undone.`
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

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-lg font-semibold text-foreground">
            Your subjects
          </h2>
          <p className="text-sm text-muted-foreground">
            {subjects.length} subject{subjects.length === 1 ? "" : "s"} — one is
            picked at random per send
          </p>
        </div>
        {subjects.length > 0 && (
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
        )}
      </div>

      {subjects.length > 0 && (
        <Input
          label="Search subjects"
          placeholder="Filter subject lines..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="max-w-md"
        />
      )}

      {filtered.length === 0 ? (
        <div className="rounded-xl border border-dashed border-border px-4 py-8 text-center">
          <p className="text-sm text-muted-foreground">
            {subjects.length === 0
              ? "No subject lines yet. Import Subjects.txt or add one above."
              : "No subjects match your search."}
          </p>
          {subjects.length === 0 && onImportFromFile && (
            <Button
              size="sm"
              className="mt-4"
              onClick={onImportFromFile}
            >
              <Upload className="h-4 w-4" />
              Import .txt file
            </Button>
          )}
        </div>
      ) : (
        <ul className="divide-y divide-border overflow-hidden rounded-2xl border border-border bg-white shadow-soft">
          {filtered.map((subject, index) => (
            <li
              key={subject.id}
              className="flex items-center justify-between gap-3 px-4 py-3 sm:px-5"
            >
              <div className="flex min-w-0 items-start gap-3">
                <span className="mt-0.5 shrink-0 text-xs font-medium tabular-nums text-muted-foreground">
                  {String(index + 1).padStart(2, "0")}
                </span>
                <span className="text-sm text-foreground">{subject.text}</span>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  void onDelete(subject.id).catch(() => undefined);
                }}
                className="shrink-0 text-red-600 hover:bg-red-50"
              >
                <Trash2 className="h-4 w-4" />
                Remove
              </Button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
