// Real-time admin search: keeps only matching rows and floats the best matches to the top.
export function filterRank(rows, query, fields) {
  const q = (query || "").trim().toLowerCase();
  if (!q) return rows;
  const scored = rows
    .map((row) => {
      const haystack = fields
        .map((field) => String(field(row) ?? ""))
        .join(" ")
        .toLowerCase();
      let score = -1;
      if (haystack.includes(q)) score = haystack.startsWith(q) ? 2 : 1;
      return { row, score };
    })
    .filter((entry) => entry.score >= 0);
  scored.sort((a, b) => b.score - a.score);
  return scored.map((entry) => entry.row);
}
