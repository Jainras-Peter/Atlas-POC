import { Component, FormEvent, ReactNode, useCallback, useEffect, useRef, useState } from "react";
import { loadConversation, resumeChat, streamChat } from "../api/chat";
import { listConversations } from "../api/conversations";
import ChatComposer from "../components/chat/ChatComposer";
import ChatEmptyState from "../components/chat/ChatEmptyState";
import ChatHeader from "../components/chat/ChatHeader";
import ChatTranscript from "../components/chat/ChatTranscript";
import ThreadHistoryPanel from "../components/chat/ThreadHistoryPanel";
import { unwrapAssistantContent } from "../lib/unwrapContent";
import type { ChatMessage, ConversationSummary, StreamEvent } from "../types";

const THREAD_KEY = "atlas_sdr_thread_id";
const HISTORY_KEY = "atlas_sdr_history_open";

function newId() {
  return crypto.randomUUID();
}

/** Prevent a Markdown parse/render crash from blanking the whole transcript. */
class SoftBoundary extends Component<
  { children: ReactNode; fallback?: ReactNode },
  { error: boolean }
> {
  state = { error: false };
  static getDerivedStateFromError() {
    return { error: true };
  }
  componentDidCatch(error: unknown) {
    console.error("Chat render error", error);
  }
  render() {
    if (this.state.error) {
      return this.props.fallback ?? (
        <div className="assistant-text">Could not render this message.</div>
      );
    }
    return this.props.children;
  }
}

export default function AtlasChatPage() {
  const [threadId, setThreadId] = useState(() => {
    return localStorage.getItem(THREAD_KEY) || newId();
  });
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [historyOpen, setHistoryOpen] = useState(() => {
    const stored = localStorage.getItem(HISTORY_KEY);
    return stored === null ? true : stored === "true";
  });
  const [threads, setThreads] = useState<ConversationSummary[]>([]);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Keep a mirror of messages so hydrate cannot race-wipe a live stream.
  const messagesRef = useRef<ChatMessage[]>([]);
  const busyRef = useRef(false);
  const hydrateGenRef = useRef(0);
  const skipHydrateRef = useRef(!localStorage.getItem(THREAD_KEY));
  const streamingAssistantIdRef = useRef<string | null>(null);
  /** True while /chat/resume is in flight — ignore re-emitted approval events. */
  const resumingRef = useRef(false);
  const wasBusyRef = useRef(false);

  const commitMessages = useCallback(
    (updater: ChatMessage[] | ((current: ChatMessage[]) => ChatMessage[])) => {
      const next =
        typeof updater === "function" ? updater(messagesRef.current) : updater;
      messagesRef.current = next;
      setMessages(next);
    },
    [],
  );

  const refreshThreads = useCallback(async () => {
    try {
      const list = await listConversations();
      setThreads(list);
    } catch {
      /* history is best-effort */
    }
  }, []);

  useEffect(() => {
    localStorage.setItem(THREAD_KEY, threadId);
    if (skipHydrateRef.current) {
      skipHydrateRef.current = false;
      return;
    }

    const gen = ++hydrateGenRef.current;
    let cancelled = false;

    loadConversation(threadId)
      .then((conversation) => {
        // Ignore stale hydrates and never clobber an in-flight stream
        if (cancelled || gen !== hydrateGenRef.current || busyRef.current) {
          return;
        }
        // IMPORTANT: do NOT setMessages([]) on empty — that was wiping SSE updates
        // (React StrictMode remount + empty thread race).
        if (!conversation?.messages.length) {
          return;
        }
        const mapped = conversation.messages.map((item) => ({
          id: newId(),
          role: item.role as ChatMessage["role"],
          content: item.content,
          user: item.user,
          quote: item.quote,
          quotes: item.quotes,
          quotesCustomer: item.quotesCustomer,
          companies: item.companies,
          customers: item.customers,
          approval: item.approval,
          // Waiting cards stay clickable until Approve/Reject (execution_id)
          approvalResolved: false,
        }));
        commitMessages(mapped);
      })
      .catch(() => {
        /* keep whatever is on screen */
      });

    return () => {
      cancelled = true;
    };
  }, [threadId, commitMessages]);

  useEffect(() => {
    void refreshThreads();
  }, [refreshThreads, threadId]);

  // Refresh history once when a stream finishes — not on every busy toggle
  // (avoids flooding /conversations while Approve/Reject is in flight).
  useEffect(() => {
    if (wasBusyRef.current && !busy) {
      void refreshThreads();
    }
    wasBusyRef.current = busy;
  }, [busy, refreshThreads]);

  useEffect(() => {
    localStorage.setItem(HISTORY_KEY, String(historyOpen));
  }, [historyOpen]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, busy]);

  /** Index of the latest user bubble — assistant/approval for this turn go after it. */
  function lastUserIndex(list: ChatMessage[]) {
    for (let i = list.length - 1; i >= 0; i -= 1) {
      if (list[i].role === "user") return i;
    }
    return -1;
  }

  /** Drop trailing status rows so we can append after the user turn. */
  function trimTrailingStatus(list: ChatMessage[]) {
    const next = [...list];
    while (next.length && next[next.length - 1].role === "status") {
      next.pop();
    }
    return next;
  }

  function attachToLastAssistant(patch: Partial<ChatMessage>) {
    commitMessages((current) => {
      const next = [...current];
      const userIdx = lastUserIndex(next);
      // Only patch an assistant that belongs to the current turn (after last user)
      for (let i = next.length - 1; i > userIdx; i -= 1) {
        if (next[i].role === "assistant") {
          next[i] = { ...next[i], ...patch };
          return next;
        }
      }
      // No assistant yet this turn — create one so the card still appears below the user
      return [
        ...trimTrailingStatus(next),
        { id: newId(), role: "assistant", content: "", ...patch },
      ];
    });
  }

  function handleStreamEvent(event: StreamEvent) {
    if (event.type === "thread" && event.thread_id && event.thread_id !== threadId) {
      skipHydrateRef.current = true;
      setThreadId(event.thread_id);
    }

    if (event.type === "status" && event.message) {
      commitMessages((current) => {
        const next = [...current];
        const last = next[next.length - 1];
        if (last?.role === "status") {
          next[next.length - 1] = { ...last, content: event.message! };
          return next;
        }
        return [...next, { id: newId(), role: "status", content: event.message! }];
      });
    }

    if (event.type === "assistant_delta" && event.content) {
      const piece = unwrapAssistantContent(event.content);
      commitMessages((current) => {
        const next = [...current];
        const streamId = streamingAssistantIdRef.current;
        if (streamId) {
          const idx = next.findIndex((m) => m.id === streamId);
          const userIdx = lastUserIndex(next);
          // Only continue streaming into a bubble from this turn
          if (idx > userIdx) {
            next[idx] = { ...next[idx], content: next[idx].content + piece };
            return next;
          }
        }
        const trimmed = trimTrailingStatus(next);
        const id = newId();
        streamingAssistantIdRef.current = id;
        return [...trimmed, { id, role: "assistant", content: piece }];
      });
    }

    if (event.type === "assistant" && event.content) {
      const full = unwrapAssistantContent(event.content);
      commitMessages((current) => {
        const next = [...current];
        const streamId = streamingAssistantIdRef.current;
        const userIdx = lastUserIndex(next);
        if (streamId) {
          const idx = next.findIndex((m) => m.id === streamId);
          if (idx > userIdx) {
            next[idx] = { ...next[idx], content: full };
            return next;
          }
        }
        // Always append below the latest user message — never rewrite older turns
        const trimmed = trimTrailingStatus(next);
        const id = newId();
        streamingAssistantIdRef.current = id;
        return [...trimmed, { id, role: "assistant", content: full }];
      });
    }

    if (event.type === "approval" && event.approval) {
      // Resume re-runs the sales node; ignore stray approval frames mid-resume.
      if (resumingRef.current) {
        return;
      }
      commitMessages((current) => {
        const userIdx = lastUserIndex(current);
        // Idempotent: one pending approval card per user turn
        for (let i = current.length - 1; i > userIdx; i -= 1) {
          if (
            current[i].role === "assistant" &&
            current[i].approval &&
            !current[i].approvalResolved
          ) {
            return current;
          }
        }
        const trimmed = trimTrailingStatus(current);
        // Prefer filling an empty assistant bubble created this turn; else append
        for (let i = trimmed.length - 1; i > userIdx; i -= 1) {
          if (trimmed[i].role === "assistant" && !trimmed[i].approval) {
            const copy = [...trimmed];
            copy[i] = {
              ...copy[i],
              approval: event.approval,
              approvalResolved: false,
              content:
                copy[i].content ||
                event.approval?.message ||
                "Please approve or reject this action.",
            };
            return copy;
          }
        }
        return [
          ...trimmed,
          {
            id: newId(),
            role: "assistant",
            content:
              event.approval?.message || "Please approve or reject this action.",
            approval: event.approval,
            approvalResolved: false,
          },
        ];
      });
    }

    if (event.type === "result" && event.user) {
      attachToLastAssistant({ user: event.user });
    }
    if (event.type === "result" && event.quote) {
      attachToLastAssistant({ quote: event.quote });
    }
    if (event.type === "result" && event.companies) {
      attachToLastAssistant({ companies: event.companies });
    }
    if (event.type === "result" && event.customers) {
      attachToLastAssistant({ customers: event.customers });
    }
    if (event.type === "quotes" && event.quotes) {
      attachToLastAssistant({
        quotes: event.quotes,
        quotesCustomer: event.customer,
      });
    }
    if (event.type === "error") {
      commitMessages((current) => [
        ...current,
        {
          id: newId(),
          role: "assistant",
          content: event.message || "Something went wrong.",
        },
      ]);
    }
  }

  async function sendMessage(text: string) {
    const trimmed = text.trim();
    if (!trimmed || busyRef.current) return;

    setInput("");
    streamingAssistantIdRef.current = null;
    // Bump hydrate gen so any in-flight empty hydrate cannot wipe this turn
    hydrateGenRef.current += 1;
    busyRef.current = true;
    setBusy(true);

    commitMessages((current) => [
      ...current,
      { id: newId(), role: "user", content: trimmed },
    ]);

    try {
      const isImport =
        /\bimport\b|save to atlas|add to atlas|add (the |these )?users?\b.*\batlas\b/i.test(
          trimmed,
        );
      let extras:
        | {
            customers?: ChatMessage["customers"];
            companies?: ChatMessage["companies"];
          }
        | undefined;
      if (isImport) {
        // Re-send last discovery cards so Sales HITL has data even if
        // graph state was wiped by a prior SDR turn.
        const withCustomers = [...messagesRef.current]
          .reverse()
          .find((m) => m.customers && m.customers.length > 0);
        const withCompanies = [...messagesRef.current]
          .reverse()
          .find((m) => m.companies && m.companies.length > 0);
        extras = {
          customers: withCustomers?.customers,
          companies: withCompanies?.companies,
        };
      }
      await streamChat(trimmed, threadId, handleStreamEvent, extras);
    } catch (error) {
      commitMessages((current) => [
        ...current,
        {
          id: newId(),
          role: "assistant",
          content: error instanceof Error ? error.message : "Chat failed",
        },
      ]);
    } finally {
      busyRef.current = false;
      setBusy(false);
      streamingAssistantIdRef.current = null;
      // Ensure React state matches the mirror after the stream
      setMessages(messagesRef.current);
    }
  }

  async function decideApproval(messageId: string, approved: boolean) {
    // Idempotent: ignore double-clicks / duplicate Approve while resume runs
    if (busyRef.current || resumingRef.current) return;
    const target = messagesRef.current.find((m) => m.id === messageId);
    if (!target?.approval || target.approvalResolved) return;
    const executionId = target.approval.execution_id;
    if (!executionId) {
      commitMessages((current) => [
        ...current,
        {
          id: newId(),
          role: "assistant",
          content:
            "This approval is from an older session. Please ask to import/delete again.",
        },
      ]);
      return;
    }

    hydrateGenRef.current += 1;
    busyRef.current = true;
    resumingRef.current = true;
    setBusy(true);
    streamingAssistantIdRef.current = null;

    commitMessages((current) =>
      current.map((m) =>
        m.id === messageId ? { ...m, approvalResolved: true } : m,
      ),
    );
    commitMessages((current) => [
      ...current,
      {
        id: newId(),
        role: "user",
        content: approved ? "[Approve]" : "[Reject]",
      },
    ]);

    try {
      await resumeChat(threadId, approved, handleStreamEvent, executionId);
    } catch (error) {
      // Re-open the card so the user can retry if resume failed
      commitMessages((current) =>
        current.map((m) =>
          m.id === messageId ? { ...m, approvalResolved: false } : m,
        ),
      );
      commitMessages((current) => [
        ...current,
        {
          id: newId(),
          role: "assistant",
          content: error instanceof Error ? error.message : "Resume failed",
        },
      ]);
    } finally {
      resumingRef.current = false;
      busyRef.current = false;
      setBusy(false);
      streamingAssistantIdRef.current = null;
      setMessages(messagesRef.current);
    }
  }

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    void sendMessage(input);
  }

  function startNewChat() {
    const next = newId();
    skipHydrateRef.current = true;
    hydrateGenRef.current += 1;
    localStorage.setItem(THREAD_KEY, next);
    setThreadId(next);
    commitMessages([]);
    setInput("");
    streamingAssistantIdRef.current = null;
  }

  function selectThread(id: string) {
    if (id === threadId) return;
    skipHydrateRef.current = false;
    hydrateGenRef.current += 1;
    commitMessages([]); // intentional clear when switching threads
    setThreadId(id);
  }

  function selectCompany(companyId: string) {
    void sendMessage(
      `I choose company ${companyId}. Please show full company details.`,
    );
  }

  const empty = messages.length === 0;

  return (
    <div className={`atlas-workspace ${historyOpen ? "with-history" : ""}`}>
      <div className="atlas-main">
        <ChatHeader
          historyOpen={historyOpen}
          onToggleHistory={() => setHistoryOpen((v) => !v)}
        />
        <div className="atlas-body">
          {empty ? (
            <ChatEmptyState onSuggestion={(text) => setInput(text)} />
          ) : (
            <SoftBoundary>
              <ChatTranscript
                messages={messages}
                busy={busy}
                onSelectCompany={selectCompany}
                onApprove={(id) => void decideApproval(id, true)}
                onReject={(id) => void decideApproval(id, false)}
                bottomRef={bottomRef}
              />
            </SoftBoundary>
          )}
          <ChatComposer
            value={input}
            busy={busy}
            onChange={setInput}
            onSubmit={onSubmit}
            showChips={empty}
            onChip={(text) => setInput(text)}
          />
        </div>
      </div>
      <ThreadHistoryPanel
        open={historyOpen}
        threads={threads}
        activeThreadId={threadId}
        onNewChat={startNewChat}
        onSelect={selectThread}
        onClose={() => setHistoryOpen(false)}
      />
    </div>
  );
}
