import { formatRelativeTime, groupThreadsByRecency } from "../../lib/groupThreads";
import type { ConversationSummary } from "../../types";

type Props = {
  open: boolean;
  threads: ConversationSummary[];
  activeThreadId: string;
  onNewChat: () => void;
  onSelect: (threadId: string) => void;
  onClose: () => void;
};

export default function ThreadHistoryPanel({
  open,
  threads,
  activeThreadId,
  onNewChat,
  onSelect,
  onClose,
}: Props) {
  if (!open) return null;
  const groups = groupThreadsByRecency(threads);

  return (
    <aside className="atlas-history">
      <div className="atlas-history-top">
        <button type="button" className="atlas-new-chat" onClick={onNewChat}>
          + New chat
        </button>
        <button type="button" className="ghost history-close" onClick={onClose}>
          Close
        </button>
      </div>
      <div className="atlas-history-scroll">
        {groups.length === 0 && (
          <p className="muted atlas-history-empty">No previous chats yet.</p>
        )}
        {groups.map((group) => (
          <div key={group.label} className="atlas-history-group">
            <div className="atlas-history-label">{group.label}</div>
            {group.items.map((thread) => (
              <button
                key={thread.thread_id}
                type="button"
                className={`atlas-history-item ${
                  thread.thread_id === activeThreadId ? "active" : ""
                }`}
                onClick={() => onSelect(thread.thread_id)}
              >
                <span className="atlas-history-icon" aria-hidden>
                  💬
                </span>
                <span className="atlas-history-text">
                  <span className="atlas-history-title">{thread.title}</span>
                  <span className="atlas-history-time">
                    {formatRelativeTime(thread.updated_at)}
                  </span>
                </span>
              </button>
            ))}
          </div>
        ))}
      </div>
    </aside>
  );
}
