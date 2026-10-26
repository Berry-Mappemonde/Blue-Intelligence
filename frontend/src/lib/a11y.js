/**
 * Small keyboard / focus helpers shared by the header, the sidebar and the map.
 * Pure functions, so they are testable without a DOM where possible.
 */

/** Mirror the UI language on <html lang> (screen readers pick the voice from it). */
export function applyDocumentLang(doc, lang) {
  const code = lang === "fr" ? "fr" : "en";
  if (doc && doc.documentElement && doc.documentElement.lang !== code) doc.documentElement.lang = code;
  return code;
}

/** True for the Escape key, whatever the browser reports. */
export function isEscapeKey(event) {
  return Boolean(event) && (event.key === "Escape" || event.key === "Esc" || event.keyCode === 27);
}

/** Focus `el` when it is still in the document; returns whether focus moved. */
export function restoreFocus(el, options = { preventScroll: true }) {
  if (!el || typeof el.focus !== "function" || el.isConnected === false) return false;
  try { el.focus(options); } catch (_) { return false; }
  return true;
}

/** Test id of a zone row, the element "All zones" hands focus back to. */
export function zoneRowTestId(mrgid) {
  return mrgid == null ? null : `poe-zone-row-${mrgid}`;
}
