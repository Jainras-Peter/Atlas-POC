type Props = {
  historyOpen: boolean;
  onToggleHistory: () => void;
};

export default function ChatHeader({ historyOpen, onToggleHistory }: Props) {
  return (
    <header className="atlas-chat-header">
      <div>
        <h1>Atlas</h1>
        <p>Supervisor · find leads, import contacts, manage users.</p>
      </div>
      <button
        type="button"
        className={`history-toggle ${historyOpen ? "active" : ""}`}
        onClick={onToggleHistory}
        aria-label="Toggle chat history"
        title="Chat history"
      >
        <svg
          width="20"
          height="20"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden
        >
          <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" />
          <path d="M3 3v5h5" />
          <path d="M12 7v5l4 2" />
        </svg>
      </button>
    </header>
  );
}
