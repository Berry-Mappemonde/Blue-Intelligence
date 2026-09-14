/**
 * Acceptance of "this map is not for navigation".
 * The banner stays visible; this key only records whether the user
 * clicked to enter. If the text changes (version), we ask again.
 */
export const NOT_FOR_NAV_STORAGE_KEY = "bi.notForNav.accepted";
export const NOT_FOR_NAV_VERSION = "2026-09-14.v2";

export function disclaimerFingerprint(title, body) {
  const text = `${NOT_FOR_NAV_VERSION}\n${title || ""}\n${body || ""}`;
  let h = 2166136261;
  for (let i = 0; i < text.length; i += 1) {
    h ^= text.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return (h >>> 0).toString(16).padStart(8, "0");
}

export function readNotForNavAccepted(storage, title, body) {
  try {
    const raw = (storage || localStorage).getItem(NOT_FOR_NAV_STORAGE_KEY);
    if (!raw) return false;
    const rec = JSON.parse(raw);
    const fp = disclaimerFingerprint(title, body);
    return rec?.version === NOT_FOR_NAV_VERSION && rec?.textKey === fp;
  } catch (_) {
    return false;
  }
}

export function writeNotForNavAccepted(storage, title, body) {
  const rec = {
    version: NOT_FOR_NAV_VERSION,
    textKey: disclaimerFingerprint(title, body),
    at: new Date().toISOString(),
  };
  try {
    (storage || localStorage).setItem(NOT_FOR_NAV_STORAGE_KEY, JSON.stringify(rec));
  } catch (_) { /* quota / private */ }
  return rec;
}

/** Until the warning is accepted, the site stays closed. */
export function siteEntryNeedsAccept(accepted) {
  return !accepted;
}
