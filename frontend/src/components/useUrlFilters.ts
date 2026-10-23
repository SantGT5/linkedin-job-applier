import { useSearchParams } from "react-router-dom";

/** Filters and page live in the URL, so a view can be bookmarked and Back works. */
export function useUrlFilters<K extends string>(keys: readonly K[]) {
  const [params, setParams] = useSearchParams();
  const values = Object.fromEntries(keys.map((k) => [k, params.get(k) ?? ""])) as Record<K, string>;
  const page = Math.max(1, Number(params.get("page") ?? "1") || 1);

  function setFilter(key: K, value: string) {
    setParams(
      (current) => {
        const next = new URLSearchParams(current);
        if (value) next.set(key, value);
        else next.delete(key);
        next.delete("page");
        return next;
      },
      { replace: true },
    );
  }

  function setPage(value: number) {
    setParams((current) => {
      const next = new URLSearchParams(current);
      if (value > 1) next.set("page", String(value));
      else next.delete("page");
      return next;
    });
  }

  function query(extra: Record<string, string> = {}) {
    const q = new URLSearchParams();
    for (const key of keys) if (values[key]) q.set(key, values[key]);
    q.set("page", String(page));
    q.set("page_size", "25");
    for (const [k, v] of Object.entries(extra)) q.set(k, v);
    return q.toString();
  }

  return { values, page, setFilter, setPage, query, params, setParams };
}
