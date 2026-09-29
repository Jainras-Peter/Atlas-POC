import type { ConversationSummary } from "../types";

export async function listConversations(): Promise<ConversationSummary[]> {
  const response = await fetch("/api/conversations");
  if (!response.ok) throw new Error("Failed to list conversations");
  return (await response.json()) as ConversationSummary[];
}

export async function deleteConversation(threadId: string): Promise<void> {
  const response = await fetch(`/api/conversations/${threadId}`, {
    method: "DELETE",
  });
  if (!response.ok) throw new Error("Failed to delete conversation");
}
