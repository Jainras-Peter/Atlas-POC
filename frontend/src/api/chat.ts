import type { CompanyHit, ConversationOut, CustomerHit, StreamEvent } from "../types";

async function readSseStream(
  response: Response,
  onEvent: (event: StreamEvent) => void,
): Promise<void> {
  if (!response.ok || !response.body) {
    throw new Error(`Chat request failed (${response.status})`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    // Support both \n\n and \r\n\r\n event separators
    const parts = buffer.split(/\r?\n\r?\n/);
    buffer = parts.pop() ?? "";

    for (const part of parts) {
      if (!part.trim()) continue;
      const dataLines = part
        .split(/\r?\n/)
        .filter((line) => line.startsWith("data:"))
        .map((line) => line.replace(/^data:\s?/, ""));
      if (!dataLines.length) continue;
      const raw = dataLines.join("\n");
      try {
        onEvent(JSON.parse(raw) as StreamEvent);
      } catch {
        // One bad frame must not kill the whole stream / wipe the UI
        console.warn("Skipping malformed SSE frame", raw.slice(0, 200));
      }
    }
  }
}

export async function streamChat(
  message: string,
  threadId: string,
  onEvent: (event: StreamEvent) => void,
  extras?: {
    customers?: CustomerHit[];
    companies?: CompanyHit[];
    locked_company_id?: string;
  },
): Promise<void> {
  const response = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      message,
      thread_id: threadId,
      customers: extras?.customers,
      companies: extras?.companies,
      locked_company_id: extras?.locked_company_id,
    }),
  });
  await readSseStream(response, onEvent);
}

/** Resolve a parked Sales execution (Approve / Reject) by execution_id. */
export async function resumeChat(
  threadId: string,
  approved: boolean,
  onEvent: (event: StreamEvent) => void,
  executionId: string,
): Promise<void> {
  const response = await fetch("/api/chat/resume", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      thread_id: threadId,
      approved,
      execution_id: executionId,
    }),
  });
  await readSseStream(response, onEvent);
}

export async function loadConversation(threadId: string): Promise<ConversationOut | null> {
  const response = await fetch(`/api/conversations/${threadId}`);
  if (response.status === 404) return null;
  if (!response.ok) throw new Error("Failed to load conversation");
  const conversation = (await response.json()) as ConversationOut;
  if (!conversation.messages?.length) return null;
  return conversation;
}
