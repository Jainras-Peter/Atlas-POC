import { useEffect, useMemo, useState } from "react";
import { fetchUsers } from "../api/users";
import { formatRelativeTime, groupThreadsByRecency } from "../lib/groupThreads";
import type { Customer } from "../types";

type UserGroup = { label: string; items: Customer[] };

function groupUsers(users: Customer[]): UserGroup[] {
  // Reuse day bucketing — map ConversationSummary shape
  const asThreads = users.map((u) => ({
    ...u,
    updated_at: u.created_at,
  }));
  return groupThreadsByRecency(asThreads).map((g) => ({
    label: g.label,
    items: g.items,
  }));
}

export default function UsersPage() {
  const [users, setUsers] = useState<Customer[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      setUsers(await fetchUsers());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load users");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    const onFocus = () => {
      load();
    };
    window.addEventListener("focus", onFocus);
    return () => window.removeEventListener("focus", onFocus);
  }, []);

  const groups = useMemo(() => groupUsers(users), [users]);

  return (
    <div className="users-page">
      <div className="page-header">
        <p className="muted">
          {loading ? "Loading..." : `${users.length} customers · grouped by import time`}
        </p>
        <button type="button" onClick={load} disabled={loading}>
          Refresh
        </button>
      </div>
      {error && <p className="error">{error}</p>}
      {loading && <p className="muted">Loading users...</p>}
      {!loading && users.length === 0 && (
        <p className="muted">
          No users yet. Ask Atlas to find contacts, then say &quot;Import this&quot; and
          Approve.
        </p>
      )}
      {groups.map((group) => (
        <section key={group.label} className="users-group">
          <h2 className="users-group-title">{group.label}</h2>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Email</th>
                  <th>Age</th>
                  <th>Contact</th>
                  <th>Active</th>
                  <th>Imported</th>
                  <th>ID</th>
                </tr>
              </thead>
              <tbody>
                {group.items.map((user) => (
                  <tr key={user.id}>
                    <td>{user.name}</td>
                    <td>{user.email}</td>
                    <td>{user.age ?? "—"}</td>
                    <td>{user.contact_number ?? "—"}</td>
                    <td>
                      <span className={user.is_active ? "badge on" : "badge off"}>
                        {user.is_active ? "Yes" : "No"}
                      </span>
                    </td>
                    <td className="muted">{formatRelativeTime(user.created_at)}</td>
                    <td className="mono">{user.id}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ))}
    </div>
  );
}
