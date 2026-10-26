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

/**
 * Track how the user last interacted (pointer or keyboard) on <html data-input>,
 * so a focus ring moved by script (the sheet heading) shows only after keyboard use.
 */
export function installInputModality(doc) {
  if (!doc || !doc.documentElement || doc.documentElement.dataset?.inputTracked === "1") return () => {};
  const root = doc.documentElement;
  root.dataset.inputTracked = "1";
  const pointer = () => { root.dataset.input = "pointer"; };
  const keyboard = (e) => { if (!e || e.key !== "Shift") root.dataset.input = "keyboard"; };
  doc.addEventListener("pointerdown", pointer, true);
  doc.addEventListener("mousedown", pointer, true);
  doc.addEventListener("keydown", keyboard, true);
  return () => {
    doc.removeEventListener("pointerdown", pointer, true);
    doc.removeEventListener("mousedown", pointer, true);
    doc.removeEventListener("keydown", keyboard, true);
    delete root.dataset.inputTracked;
  };
}

/** Test id of a zone row, the element "All zones" hands focus back to. */
export function zoneRowTestId(mrgid) {
  return mrgid == null ? null : `poe-zone-row-${mrgid}`;
}
