type ThreadGroup = "Recent" | "Yesterday" | "Older";

export function groupThreadsByRecency<T extends { updated_at: string }>(
  threads: T[],
): { label: ThreadGroup; items: T[] }[] {
  const now = new Date();
  const startToday = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const startYesterday = new Date(startToday);
  startYesterday.setDate(startYesterday.getDate() - 1);

  const buckets: Record<ThreadGroup, T[]> = {
    Recent: [],
    Yesterday: [],
    Older: [],
  };

  for (const thread of threads) {
    const updated = new Date(thread.updated_at);
    if (updated >= startToday) buckets.Recent.push(thread);
    else if (updated >= startYesterday) buckets.Yesterday.push(thread);
    else buckets.Older.push(thread);
  }

  return (["Recent", "Yesterday", "Older"] as ThreadGroup[])
    .map((label) => ({ label, items: buckets[label] }))
    .filter((group) => group.items.length > 0);
}

export function formatRelativeTime(iso: string): string {
  const then = new Date(iso).getTime();
  const diffMs = Date.now() - then;
  const mins = Math.floor(diffMs / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}
