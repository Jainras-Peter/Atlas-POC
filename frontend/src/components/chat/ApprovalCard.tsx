import type { ApprovalRequest } from "../../types";

type Props = {
  approval: ApprovalRequest;
  disabled?: boolean;
  onApprove: () => void;
  onReject: () => void;
};

export default function ApprovalCard({
  approval,
  disabled,
  onApprove,
  onReject,
}: Props) {
  const users = approval.users || [];
  const actionLabel = approval.action === "delete" ? "Delete" : "Import";

  return (
    <div className="approval-card">
      <div className="approval-card-title">
        Human approval required
        <span className="approval-badge">{actionLabel}</span>
      </div>
      <p className="approval-message">
        {approval.message || `Can I ${actionLabel.toLowerCase()} the following?`}
      </p>
      {users.length > 0 && (
        <ul className="approval-user-list">
          {users.map((user, index) => (
            <li key={user.id || user.email || String(index)}>
              <strong>{user.name || "—"}</strong>
              <span className="muted">
                {" "}
                · {user.email || "no email"}
                {user.id ? ` · ${user.id}` : ""}
              </span>
            </li>
          ))}
        </ul>
      )}
      <div className="approval-actions">
        <button
          type="button"
          className="approval-reject"
          disabled={disabled}
          onClick={onReject}
        >
          Reject
        </button>
        <button
          type="button"
          className="approval-approve"
          disabled={disabled}
          onClick={onApprove}
        >
          Approve
        </button>
      </div>
    </div>
  );
}
