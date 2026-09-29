import { useEffect, useState } from "react";
import { fetchQuotes } from "../api/quotes";
import QuotesTable from "../components/QuotesTable";
import type { Quote } from "../types";

export default function QuotesPage() {
  const [quotes, setQuotes] = useState<Quote[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      setQuotes(await fetchQuotes());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load quotes");
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

  return (
    <div className="users-page quotes-page">
      <div className="page-header">
        <p className="muted">{loading ? "Loading..." : `${quotes.length} Results Found`}</p>
        <button type="button" onClick={load} disabled={loading}>
          Refresh
        </button>
      </div>
      {error && <p className="error">{error}</p>}
      {!loading && quotes.length === 0 && (
        <p className="muted">No quotes yet. Create one from Chat.</p>
      )}
      {quotes.length > 0 && <QuotesTable quotes={quotes} />}
    </div>
  );
}
