/**
 * Attribution bar, presentation only: every provider once, whatever the layers add.
 * Leaflet joins each layer's attribution string; raster and vector basemaps, the
 * overlay and the WMS layers repeat "© OpenStreetMap contributors" and "© Open Waters".
 */

const SEPARATOR = /\s*(?:,|·|\|)\s*|\s+(?=©|&copy;)/;

const keyOf = (part) => part
  .replace(/<[^>]+>/g, "")
  .replace(/&copy;/g, "©")
  .replace(/\s+/g, " ")
  .trim()
  .toLowerCase();

/** Unique attribution items, in first-seen order, from the raw strings of every layer. */
export function uniqueAttributionItems(texts) {
  const seen = new Set();
  const items = [];
  (texts || []).forEach((text) => {
    String(text || "").split(SEPARATOR).forEach((raw) => {
      const part = raw.trim();
      const key = keyOf(part);
      if (!key || seen.has(key)) return;
      seen.add(key);
      items.push(part);
    });
  });
  return items;
}

/** Replace the control's renderer so it prints the unique items (same markup as Leaflet). */
export function installAttributionDedupe(control) {
  if (!control || control._biDedupe) return;
  control._biDedupe = true;
  control._update = function update() {
    if (!this._map || !this._container) return;
    const texts = Object.keys(this._attributions || {}).filter((k) => this._attributions[k]);
    const items = uniqueAttributionItems(texts);
    const prefix = this.options?.prefix;
    this._container.innerHTML = [prefix, items.join(", ")]
      .filter(Boolean)
      .join(' <span aria-hidden="true">|</span> ');
  };
  try { control._update(); } catch (_) { /* not on a map yet */ }
}
