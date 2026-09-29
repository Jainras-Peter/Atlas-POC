import { useEffect, useRef, useState } from "react";
import { downloadQuotesExcel } from "../api/quotes";
import type { Quote } from "../types";

type QuotesTableProps = {
  quotes: Quote[];
  customerId?: string;
  email?: string;
};

export default function QuotesTable({
  quotes,
  customerId,
  email,
}: QuotesTableProps) {
  const [menuOpen, setMenuOpen] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!menuOpen) return;
    function onPointerDown(event: MouseEvent) {
      if (!menuRef.current?.contains(event.target as Node)) {
        setMenuOpen(false);
      }
    }
    document.addEventListener("mousedown", onPointerDown);
    return () => document.removeEventListener("mousedown", onPointerDown);
  }, [menuOpen]);

  if (!quotes.length) {
    return <p className="muted">No quotes found.</p>;
  }

  async function onExcelDownload() {
    setError(null);
    setDownloading(true);
    setMenuOpen(false);
    try {
      await downloadQuotesExcel({ customerId, email });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Download failed");
    } finally {
      setDownloading(false);
    }
  }

  return (
    <div className="quotes-table-block">
      <div className="quotes-table-toolbar">
        <div className="download-menu" ref={menuRef}>
          <button
            type="button"
            className="download-btn"
            onClick={() => setMenuOpen((open) => !open)}
            disabled={downloading}
          >
            {downloading ? "Downloading..." : "Download"}
          </button>
          {menuOpen && (
            <div className="format-menu" role="menu">
              <button
                type="button"
                className="format-option"
                role="menuitem"
                onClick={onExcelDownload}
              >
                Excel (.xlsx)
              </button>
              <button type="button" className="format-option" disabled title="Coming soon">
                PDF (Coming soon)
              </button>
              <button type="button" className="format-option" disabled title="Coming soon">
                CSV (Coming soon)
              </button>
            </div>
          )}
        </div>
      </div>
      {error && <p className="error download-error">{error}</p>}
      <div className="table-wrap chat-quotes-table">
        <table>
          <thead>
            <tr>
              <th>Reference</th>
              <th>Type</th>
              <th>Contact Email</th>
              <th>Customer Name</th>
              <th>Mode</th>
              <th>Origin</th>
              <th>Destination</th>
              <th>Cargo</th>
              <th>Cut Off</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {quotes.map((quote) => (
              <tr key={quote.id}>
                <td className="mono linkish">{quote.quote_number}</td>
                <td>{quote.type}</td>
                <td>{quote.contact_email}</td>
                <td>{quote.customer_name}</td>
                <td>{quote.mode}</td>
                <td>{quote.origin}</td>
                <td>{quote.destination}</td>
                <td>{quote.cargo}</td>
                <td>{quote.cut_off_date}</td>
                <td>
                  <span className={quote.status === "WON" ? "badge on" : "badge pending"}>
                    {quote.status}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
