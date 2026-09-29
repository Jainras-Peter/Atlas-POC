import type { Quote } from "../types";

export async function fetchQuotes(params?: {
  customerId?: string;
  email?: string;
}): Promise<Quote[]> {
  const query = new URLSearchParams();
  if (params?.customerId) query.set("customer_id", params.customerId);
  if (params?.email) query.set("email", params.email);
  const suffix = query.toString() ? `?${query}` : "";
  const response = await fetch(`/api/quotes${suffix}`);
  if (!response.ok) throw new Error("Failed to load quotes");
  return response.json();
}

function filenameFromDisposition(header: string | null): string | null {
  if (!header) return null;
  const match = header.match(/filename="?([^"]+)"?/i);
  return match?.[1] ?? null;
}

export async function downloadQuotesExcel(params?: {
  customerId?: string;
  email?: string;
}): Promise<void> {
  const query = new URLSearchParams({ format: "xlsx" });
  if (params?.customerId) query.set("customer_id", params.customerId);
  if (params?.email) query.set("email", params.email);

  const response = await fetch(`/api/quotes/export?${query}`);
  if (!response.ok) {
    let detail = "Failed to download quotes";
    try {
      const body = await response.json();
      if (typeof body?.detail === "string") detail = body.detail;
    } catch {
      // keep default
    }
    throw new Error(detail);
  }

  const blob = await response.blob();
  const filename =
    filenameFromDisposition(response.headers.get("Content-Disposition")) ||
    "quotes.xlsx";
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}
