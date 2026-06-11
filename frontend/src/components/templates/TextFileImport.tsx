"use client";

import {
  forwardRef,
  useCallback,
  useImperativeHandle,
  useRef,
  useState,
} from "react";
import { ChevronDown, Upload } from "lucide-react";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { cn } from "@/lib/utils";

export interface TextFileImportHandle {
  openFilePicker: () => void;
  expand: () => void;
}

interface TextFileImportProps {
  label: string;
  hint: string;
  example: string;
  sampleFileHint?: string;
  onImport: (file: File) => Promise<{ imported: number; skipped: number; errors: string[] }>;
  onComplete: () => void;
  defaultOpen?: boolean;
}

export const TextFileImport = forwardRef<TextFileImportHandle, TextFileImportProps>(
  function TextFileImport(
    {
      label,
      hint,
      example,
      sampleFileHint,
      onImport,
      onComplete,
      defaultOpen = true,
    },
    ref
  ) {
    const fileRef = useRef<HTMLInputElement>(null);
    const [open, setOpen] = useState(defaultOpen);
    const [importing, setImporting] = useState(false);
    const [dragging, setDragging] = useState(false);
    const [error, setError] = useState("");
    const [success, setSuccess] = useState("");

    useImperativeHandle(ref, () => ({
      openFilePicker: () => {
        setOpen(true);
        fileRef.current?.click();
      },
      expand: () => setOpen(true),
    }));

    const importFile = useCallback(
      async (file: File) => {
        setError("");
        setSuccess("");
        setImporting(true);
        try {
          const result = await onImport(file);
          const skippedNote =
            result.skipped > 0 ? ` (${result.skipped} skipped)` : "";
          setSuccess(
            `Imported ${result.imported} item${result.imported === 1 ? "" : "s"}${skippedNote}.`
          );
          if (fileRef.current) fileRef.current.value = "";
          onComplete();
        } catch (err) {
          setError(err instanceof Error ? err.message : "Import failed.");
        } finally {
          setImporting(false);
        }
      },
      [onComplete, onImport]
    );

    async function handleSubmit(e: React.FormEvent) {
      e.preventDefault();
      const file = fileRef.current?.files?.[0];
      if (!file) {
        setError("Please choose a .txt file.");
        return;
      }
      await importFile(file);
    }

    function handleDrop(e: React.DragEvent) {
      e.preventDefault();
      setDragging(false);
      const file = e.dataTransfer.files?.[0];
      if (!file) return;
      if (!file.name.toLowerCase().endsWith(".txt") && file.type !== "text/plain") {
        setError("Please drop a plain text file (.txt).");
        return;
      }
      void importFile(file);
    }

    return (
      <div className="overflow-hidden rounded-2xl border border-border bg-white shadow-soft">
        <button
          type="button"
          onClick={() => setOpen((value) => !value)}
          className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left transition-colors hover:bg-stone-50"
        >
          <div>
            <p className="text-sm font-medium text-foreground">{label}</p>
            <p className="mt-0.5 text-xs text-muted-foreground">
              {open
                ? "Click to collapse"
                : sampleFileHint ?? "Click to import from a .txt file"}
            </p>
          </div>
          <ChevronDown
            className={cn(
              "h-5 w-5 shrink-0 text-muted-foreground transition-transform",
              open && "rotate-180"
            )}
          />
        </button>

        {open && (
          <form
            onSubmit={handleSubmit}
            className="space-y-4 border-t border-border bg-violet-50/20 px-4 py-4"
          >
            <p className="text-xs text-muted-foreground">{hint}</p>
            {sampleFileHint && (
              <p className="text-xs font-medium text-brand">{sampleFileHint}</p>
            )}

            <pre className="overflow-x-auto rounded-xl border border-border bg-white/80 p-3 text-xs leading-relaxed text-muted-foreground">
              {example}
            </pre>

            <div
              onDragEnter={(e) => {
                e.preventDefault();
                setDragging(true);
              }}
              onDragLeave={(e) => {
                e.preventDefault();
                setDragging(false);
              }}
              onDragOver={(e) => e.preventDefault()}
              onDrop={handleDrop}
              className={cn(
                "rounded-xl border-2 border-dashed px-4 py-6 text-center transition-colors",
                dragging
                  ? "border-brand bg-brand-subtle"
                  : "border-border bg-white/80"
              )}
            >
              <Upload className="mx-auto h-8 w-8 text-muted-foreground" />
              <p className="mt-2 text-sm text-foreground">
                Drag and drop a .txt file here
              </p>
              <p className="mt-1 text-xs text-muted-foreground">or choose a file below</p>
            </div>

            <input
              ref={fileRef}
              type="file"
              accept=".txt,text/plain"
              className="block w-full text-sm text-muted-foreground file:mr-4 file:rounded-lg file:border-0 file:bg-brand-muted file:px-4 file:py-2 file:text-sm file:font-medium file:text-brand hover:file:bg-brand-subtle"
            />

            {error && <Alert variant="danger">{error}</Alert>}
            {success && <Alert variant="success">{success}</Alert>}

            <Button type="submit" size="sm" loading={importing}>
              <Upload className="h-4 w-4" />
              Import from .txt
            </Button>
          </form>
        )}
      </div>
    );
  }
);
