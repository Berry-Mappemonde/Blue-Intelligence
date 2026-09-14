/**
 * Acceptation « NOT FOR NAVIGATION ».
 * Le bandeau reste affiché ; cette clé dit seulement si l'utilisateur
 * a cliqué Accepter. Si le texte change (version), on redemande.
 */
export const NOT_FOR_NAV_STORAGE_KEY = "bi.notForNav.accepted";
export const NOT_FOR_NAV_VERSION = "2026-09-14.v1";

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
  } catch (_) { /* quota / privé */ }
  return rec;
}

export function restrictedIntentNeedsAccept(accepted, intent) {
  if (accepted) return false;
  if (!intent) return false;
  if (intent.basemap === "sea") return true;
  if (intent.overlay) return true;
  if (intent.wms && Object.values(intent.wms).some(Boolean)) return true;
  if (intent.satellite) return true;
  return false;
}
