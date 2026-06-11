"use client";

import { useRef, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { insertAtCursor } from "@/lib/template-builder";
import { VariableChips } from "./VariableChips";

interface SubjectFormProps {
  onSubmit: (text: string) => Promise<void>;
  submitting?: boolean;
}

export function SubjectForm({ onSubmit, submitting = false }: SubjectFormProps) {
  const [text, setText] = useState("Quick question for {{name}}");
  const inputRef = useRef<HTMLInputElement>(null);

  function handleInsertVariable(token: string) {
    const el = inputRef.current;
    if (!el) {
      setText((prev) => `${prev}${token}`);
      return;
    }
    const start = el.selectionStart ?? text.length;
    const end = el.selectionEnd ?? text.length;
    const { nextValue, cursor } = insertAtCursor(text, token, start, end);
    setText(nextValue);
    requestAnimationFrame(() => {
      el.focus();
      el.setSelectionRange(cursor, cursor);
    });
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    await onSubmit(text.trim());
    setText("Quick question for {{name}}");
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <Input
        ref={inputRef}
        label="Subject line"
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="Quick question for Alex"
        required
        hint="Add several subjects — one is picked randomly for each candidate."
      />
      <VariableChips onInsert={handleInsertVariable} />
      <Button type="submit" loading={submitting} size="sm">
        Add subject
      </Button>
    </form>
  );
}
