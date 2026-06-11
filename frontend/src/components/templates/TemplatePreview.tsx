"use client";

import { Eye } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import {
  applySampleData,
  appendSignaturePreviewHtml,
} from "@/lib/template-builder";

interface TemplatePreviewProps {
  html: string;
  sampleSubject?: string;
}

export function TemplatePreview({
  html,
  sampleSubject = "Quick question for Alex",
}: TemplatePreviewProps) {
  const previewHtml = appendSignaturePreviewHtml(applySampleData(html));

  return (
    <Card className="h-full border-dashed border-violet-200 bg-violet-50/30">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-base">
          <Eye className="h-4 w-4 text-violet-600" />
          Preview
        </CardTitle>
        <p className="text-xs text-muted-foreground">
          Sample candidate: Alex — subject is chosen randomly from your subject
          list at send time.
        </p>
      </CardHeader>
      <CardContent>
        <div className="overflow-hidden rounded-xl border border-border bg-white shadow-soft">
          <div className="border-b border-border bg-stone-50 px-4 py-3">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Example subject
            </p>
            <p className="mt-1 text-sm font-medium text-foreground">
              {sampleSubject}
            </p>
          </div>
          <div
            className="prose prose-sm max-w-none px-4 py-4 text-sm text-foreground [&_a]:text-violet-600 [&_p]:mb-3 [&_p:last-child]:mb-0"
            dangerouslySetInnerHTML={{
              __html:
                previewHtml ||
                '<p class="text-muted-foreground">Your message will appear here.</p>',
            }}
          />
        </div>
        <p className="mt-3 text-xs text-muted-foreground">
          &quot;Thanks, Chris&quot; and the unsubscribe link are added
          automatically — you do not need to write them.
        </p>
      </CardContent>
    </Card>
  );
}
