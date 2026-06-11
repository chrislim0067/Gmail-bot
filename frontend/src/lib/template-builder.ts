/** Helpers to build message HTML from plain-language fields. */

export const EMAIL_SIGNATURE_PREVIEW = "Thanks\nChris";

export const TEMPLATE_VARIABLES = [
  { key: "name", label: "Name", example: "Alex" },
  { key: "first_name", label: "First name", example: "Alex" },
  { key: "last_name", label: "Last name", example: "Smith" },
  { key: "company", label: "Company", example: "Acme Inc" },
  { key: "email", label: "Email", example: "alex@example.com" },
] as const;

export type TemplateVariableKey = (typeof TEMPLATE_VARIABLES)[number]["key"];

const SAMPLE_DATA: Record<string, string> = {
  name: "Alex",
  first_name: "Alex",
  last_name: "Smith",
  company: "Acme Inc",
  email: "alex@example.com",
  unsubscribe_url: "#",
};

function escapeHtml(text: string): string {
  return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function formatParagraph(text: string): string {
  return text
    .split("\n")
    .map((line) => escapeHtml(line.trim()))
    .join("<br>");
}

/** Build stored message body (signature is added automatically when sending). */
export function buildHtmlTemplate(greeting: string, body: string): string {
  const parts: string[] = [];

  if (greeting.trim()) {
    parts.push(`<p>${formatParagraph(greeting.trim())}</p>`);
  }

  for (const block of body.split(/\n\n+/)) {
    const trimmed = block.trim();
    if (trimmed) {
      parts.push(`<p>${formatParagraph(trimmed)}</p>`);
    }
  }

  return parts.join("\n");
}

export function buildTextTemplate(greeting: string, body: string): string {
  const parts = [greeting, body].filter((s) => s.trim());
  return parts.join("\n\n");
}

export function appendSignaturePreviewHtml(html: string): string {
  return `${html}<p>Thanks<br>Chris</p>`;
}

/** Replace {{variables}} with sample values for preview. */
export function applySampleData(text: string): string {
  let result = text;
  for (const [key, value] of Object.entries(SAMPLE_DATA)) {
    result = result.replaceAll(`{{${key}}}`, value);
  }
  return result;
}

/** Decode common HTML entities from stored templates. */
export function decodeHtmlEntities(text: string): string {
  return text
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/&#x27;/gi, "'")
    .replace(/&#(\d+);/g, (_, code) =>
      String.fromCharCode(Number.parseInt(code, 10))
    )
    .replace(/&#x([0-9a-f]+);/gi, (_, hex) =>
      String.fromCharCode(Number.parseInt(hex, 16))
    );
}

/** Strip HTML tags for readable plain text. */
export function htmlToPlainSummary(html: string, maxLength?: number): string {
  const plain = decodeHtmlEntities(
    html
      .replace(/<br\s*\/?>/gi, "\n")
      .replace(/<\/p>/gi, "\n\n")
      .replace(/<p[^>]*>/gi, "")
      .replace(/<a[^>]*>.*?<\/a>/gi, "")
      .replace(/<[^>]+>/g, "")
      .replace(/\n{3,}/g, "\n\n")
      .trim()
  );

  if (maxLength === undefined || plain.length <= maxLength) return plain;
  return `${plain.slice(0, maxLength).trim()}…`;
}

export interface ReadableTemplateSource {
  html_template: string;
  text_template?: string | null;
}

/** Best plain-text body for UI display (prefers stored text_template). */
export function templateToReadableBody(
  template: ReadableTemplateSource,
  maxLength?: number
): string {
  if (template.text_template?.trim()) {
    const body = decodeHtmlEntities(
      template.text_template
        .replace(/\n---\nUnsubscribe:[\s\S]*$/, "")
        .trim()
    );
    if (maxLength === undefined || body.length <= maxLength) return body;
    return `${body.slice(0, maxLength).trim()}…`;
  }
  return htmlToPlainSummary(template.html_template, maxLength);
}

/** Sort "Version 12" style names numerically when possible. */
export function sortTemplateNames(a: string, b: string): number {
  const numA = a.match(/version\s*(\d+)/i)?.[1];
  const numB = b.match(/version\s*(\d+)/i)?.[1];
  if (numA && numB) return Number(numA) - Number(numB);
  return a.localeCompare(b, undefined, { numeric: true, sensitivity: "base" });
}

export function insertAtCursor(
  value: string,
  insertion: string,
  selectionStart: number,
  selectionEnd: number
): { nextValue: string; cursor: number } {
  const nextValue =
    value.slice(0, selectionStart) + insertion + value.slice(selectionEnd);
  const cursor = selectionStart + insertion.length;
  return { nextValue, cursor };
}
