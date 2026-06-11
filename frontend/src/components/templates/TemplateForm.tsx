"use client";

import { useMemo, useRef, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Input, Textarea } from "@/components/ui/Input";
import {
  buildHtmlTemplate,
  buildTextTemplate,
  insertAtCursor,
} from "@/lib/template-builder";
import { TemplatePreview } from "./TemplatePreview";
import { VariableChips } from "./VariableChips";

type FocusedField = "greeting" | "body";

interface TemplateFormProps {
  onSubmit: (data: {
    name: string;
    html_template: string;
    text_template: string;
  }) => Promise<void>;
  onCancel: () => void;
  submitting?: boolean;
}

export function TemplateForm({
  onSubmit,
  onCancel,
  submitting = false,
}: TemplateFormProps) {
  const [name, setName] = useState("");
  const [greeting, setGreeting] = useState("Hi {{name}},");
  const [body, setBody] = useState(
    "I wanted to reach out because I think we could help your team.\n\nWould you be open to a quick chat this week?"
  );
  const [focusedField, setFocusedField] = useState<FocusedField>("body");

  const greetingRef = useRef<HTMLTextAreaElement>(null);
  const bodyRef = useRef<HTMLTextAreaElement>(null);

  const htmlTemplate = useMemo(
    () => buildHtmlTemplate(greeting, body),
    [greeting, body]
  );

  const textTemplate = useMemo(
    () => buildTextTemplate(greeting, body),
    [greeting, body]
  );

  function handleInsertVariable(token: string) {
    const fieldMap = {
      greeting: {
        ref: greetingRef,
        value: greeting,
        setValue: setGreeting,
      },
      body: {
        ref: bodyRef,
        value: body,
        setValue: setBody,
      },
    } as const;

    const field = fieldMap[focusedField];
    const el = field.ref.current;
    if (!el) return;

    const start = el.selectionStart ?? field.value.length;
    const end = el.selectionEnd ?? field.value.length;
    const { nextValue, cursor } = insertAtCursor(
      field.value,
      token,
      start,
      end
    );

    field.setValue(nextValue);
    requestAnimationFrame(() => {
      el.focus();
      el.setSelectionRange(cursor, cursor);
    });
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    await onSubmit({
      name,
      html_template: htmlTemplate,
      text_template: textTemplate,
    });
  }

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <Card>
        <CardHeader>
          <CardTitle>Add message template</CardTitle>
          <p className="text-sm text-muted-foreground">
            Write the email body only. Subjects are added separately. Each
            candidate gets a random template and subject. &quot;Thanks, Chris&quot;
            is added automatically when sending.
          </p>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-5">
            <Input
              label="Template name"
              placeholder="e.g. Intro message #1"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
            />

            <VariableChips onInsert={handleInsertVariable} />

            <Textarea
              ref={greetingRef}
              label="Opening line"
              variant="plain"
              rows={2}
              value={greeting}
              onChange={(e) => setGreeting(e.target.value)}
              onFocus={() => setFocusedField("greeting")}
              placeholder="Hi Alex,"
            />

            <Textarea
              ref={bodyRef}
              label="Your message"
              variant="plain"
              rows={8}
              value={body}
              onChange={(e) => setBody(e.target.value)}
              onFocus={() => setFocusedField("body")}
              placeholder="Write what you want to say. Press Enter twice to start a new paragraph."
              required
              hint="Blank line = new paragraph."
            />

            <div className="flex gap-2 pt-1">
              <Button type="submit" loading={submitting}>
                Save message
              </Button>
              <Button type="button" variant="outline" onClick={onCancel}>
                Cancel
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      <TemplatePreview html={htmlTemplate} />
    </div>
  );
}
