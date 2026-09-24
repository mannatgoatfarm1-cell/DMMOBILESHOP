// Real-time admin search: keeps the source order stable so rows never jump while typing.
export function filterRank(rows, query, fields) {
  const words = (query || "").trim().toLowerCase().split(/\s+/).filter(Boolean);
  if (!words.length) return rows;
  return rows.filter((row) => fields.some((field) => {
    const value = String(field(row) ?? "").toLowerCase();
    return words.every((word) => value.includes(word));
  }));
}
