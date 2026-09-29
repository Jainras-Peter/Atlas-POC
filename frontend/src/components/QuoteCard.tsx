import type { Quote } from "../types";

type QuoteCardProps = {
  quote: Quote;
  heading?: string;
};

export default function QuoteCard({ quote, heading = "Quote details" }: QuoteCardProps) {
  const rows = [
    ["Reference", quote.quote_number],
    ["Type", quote.type],
    ["Customer", quote.customer_name],
    ["Contact email", quote.contact_email],
    ["Mode", quote.mode],
    ["Origin", quote.origin],
    ["Destination", quote.destination],
    ["Cargo", quote.cargo],
    ["Cut off", quote.cut_off_date],
    ["Status", quote.status],
  ] as const;

  return (
    <div className="user-card quote-card">
      <div className="user-card-title">{heading}</div>
      <dl className="user-card-grid">
        {rows.map(([label, value]) => (
          <div key={label} className="user-card-row">
            <dt>{label}</dt>
            <dd className={label === "Reference" ? "mono" : undefined}>
              {label === "Status" ? (
                <span className={quote.status === "WON" ? "badge on" : "badge pending"}>
                  {value}
                </span>
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
