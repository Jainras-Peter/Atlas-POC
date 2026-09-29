export function unwrapAssistantContent(raw: string): string {
  const trimmed = raw.trim();
  if (!trimmed.startsWith("[{") && !trimmed.startsWith("{")) {
    return raw;
  }

  try {
    const jsonReady = trimmed.replace(/'/g, '"');
    const parsed = JSON.parse(jsonReady) as unknown;
    const text = collectText(parsed);
    if (text) return text;
  } catch {
    const match = trimmed.match(/['"]text['"]\s*:\s*['"]([\s\S]*?)['"]\s*,\s*['"]extras['"]/);
    if (match?.[1]) {
      return decodeEscapes(match[1]);
    }
  }

  return raw;
}

function collectText(value: unknown): string {
  if (typeof value === "string") return value;
  if (Array.isArray(value)) {
    return value.map(collectText).filter(Boolean).join("\n");
  }
  if (value && typeof value === "object" && "text" in value) {
    return String((value as { text: unknown }).text);
  }
  return "";
}

function decodeEscapes(value: string): string {
  return value
    .replace(/\\n/g, "\n")
    .replace(/\\t/g, "\t")
    .replace(/\\'/g, "'")
    .replace(/\\"/g, '"');
}
