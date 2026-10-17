/** Clé du choix déjà fait par la personne. Elle passe devant DEFAULT_LANG. */
export const STORAGE_KEY = "naviguide_lang_v3";

/**
 * Langue à l'ouverture, quand rien n'est enregistré.
 * Changer cette valeur change l'application neuve.
 * Le fichier index.html doit porter le même code dans <html lang="…">.
 */
export const DEFAULT_LANG = "en";

export const VALID_LANGS = new Set(["en", "fr"]);

/** Choix enregistré s'il est connu, sinon la langue d'ouverture. */
export function resolveLang(stored) {
  return VALID_LANGS.has(stored) ? stored : DEFAULT_LANG;
}

export function readStoredLang(storage = typeof localStorage !== "undefined" ? localStorage : null) {
  const stored = storage?.getItem?.(STORAGE_KEY);
  return resolveLang(stored);
}
