import { readFileSync } from "node:fs";
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { DEFAULT_LANG, readStoredLang, resolveLang, STORAGE_KEY } from "./langStorage.js";

const html = readFileSync(new URL("../../index.html", import.meta.url), "utf8");

describe("default language", () => {
  it("opens in the language named by DEFAULT_LANG", () => {
    assert.equal(readStoredLang({ getItem: () => null }), DEFAULT_LANG);
    assert.equal(resolveLang(undefined), DEFAULT_LANG);
    assert.equal(resolveLang(""), DEFAULT_LANG);
    assert.equal(resolveLang("de"), DEFAULT_LANG);
  });

  it("keeps a language already chosen", () => {
    const mem = { getItem: (k) => (k === STORAGE_KEY ? "fr" : null) };
    assert.equal(readStoredLang(mem), "fr");
    assert.equal(resolveLang("en"), "en");
  });

  it("the first page markup uses the same opening language", () => {
    assert.match(html, new RegExp(`<html lang="${DEFAULT_LANG}">`));
  });
});
