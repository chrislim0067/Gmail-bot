/** Decode HTML entities from Gmail snippet text. */
export function decodeHtmlEntities(text: string): string {
  return text
    .replace(/&#(\d+);/g, (_, code) => String.fromCharCode(Number(code)))
    .replace(/&#x([0-9a-f]+);/gi, (_, hex) =>
      String.fromCharCode(parseInt(hex, 16))
    )
    .replace(/&quot;/g, '"')
    .replace(/&#39;|&apos;/g, "'")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&amp;/g, "&")
    .replace(/&nbsp;/g, " ");
}

/** Split Gmail-style reply snippet into new text vs quoted thread. */
export function parseReplySnippet(snippet: string): {
  body: string;
  quoted?: string;
  quoteHeader?: string;
} {
  const decoded = decodeHtmlEntities(snippet).replace(/\s+/g, " ").trim();

  const wroteMatch = decoded.match(
    /\sOn\s.+?\swrote:\s*/i
  );
  if (wroteMatch && wroteMatch.index !== undefined) {
    const body = decoded.slice(0, wroteMatch.index).trim();
    const rest = decoded.slice(wroteMatch.index).trim();
    const headerEnd = rest.search(/:\s*/);
    const quoteHeader = headerEnd >= 0 ? rest.slice(0, headerEnd + 1).trim() : undefined;
    const quoted = headerEnd >= 0 ? rest.slice(headerEnd + 1).trim() : rest;
    return { body, quoted: quoted || undefined, quoteHeader };
  }

  const originalMatch = decoded.match(/\s-{2,}\s*Original Message\s-{2,}\s*/i);
  if (originalMatch && originalMatch.index !== undefined) {
    return {
      body: decoded.slice(0, originalMatch.index).trim(),
      quoted: decoded.slice(originalMatch.index + originalMatch[0].length).trim(),
      quoteHeader: "Original message",
    };
  }

  return { body: decoded };
}

export function parseFromHeader(from: string): { name?: string; email: string } {
  const angleMatch = from.match(/^(.+?)\s*<([^>]+)>$/);
  if (angleMatch) {
    const name = angleMatch[1].trim().replace(/^["']|["']$/g, "");
    return { name: name || undefined, email: angleMatch[2].trim() };
  }
  if (from.includes("@")) {
    return { email: from.trim() };
  }
  return { email: from };
}

export function initials(name: string | undefined, email: string): string {
  if (name) {
    const parts = name.split(/\s+/).filter(Boolean);
    if (parts.length >= 2) {
      return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
    }
    return parts[0].slice(0, 2).toUpperCase();
  }
  return email.slice(0, 2).toUpperCase();
}
