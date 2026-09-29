import type { CustomerHit } from "../../types";

type Props = {
  customers: CustomerHit[];
};

export default function CustomerResultsCard({ customers }: Props) {
  if (!customers.length) return null;
  return (
    <div className="atlas-result-card">
      <div className="atlas-result-title">Customers ({customers.length})</div>
      <div className="table-wrap atlas-customers-table">
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>Role</th>
              <th>Email</th>
              <th>Country</th>
              <th>TEU</th>
            </tr>
          </thead>
          <tbody>
            {customers.map((c) => (
              <tr key={c.customerId}>
                <td>
                  <div>{c.name}</div>
                  <div className="mono muted">{c.customerId}</div>
                </td>
                <td>{c.role || "—"}</td>
                <td>{c.email || "—"}</td>
                <td>{c.country || "—"}</td>
                <td>{c.teu ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
