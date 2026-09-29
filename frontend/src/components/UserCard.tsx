import type { Customer } from "../types";

type UserCardProps = {
  user: Customer;
  heading?: string;
};

export default function UserCard({ user, heading = "Customer details" }: UserCardProps) {
  const rows = [
    ["Name", user.name],
    ["Email", user.email],
    ["Age", user.age ?? "—"],
    ["Contact number", user.contact_number ?? "—"],
    ["Active", user.is_active ? "Yes" : "No"],
    ["ID", user.id],
  ] as const;

  return (
    <div className="user-card">
      <div className="user-card-title">{heading}</div>
      <dl className="user-card-grid">
        {rows.map(([label, value]) => (
          <div key={label} className="user-card-row">
            <dt>{label}</dt>
            <dd className={label === "ID" ? "mono" : undefined}>
              {label === "Active" ? (
                <span className={user.is_active ? "badge on" : "badge off"}>{value}</span>
              ) : (
                value
              )}
            </dd>
          </div>
        ))}
      </dl>
    </div>
  );
}
