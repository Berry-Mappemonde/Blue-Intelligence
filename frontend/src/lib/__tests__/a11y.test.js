import { applyDocumentLang, isEscapeKey, restoreFocus, zoneRowTestId } from "../a11y";

describe("applyDocumentLang", () => {
  test("mirrors the UI language on <html lang>, en by default", () => {
    const doc = { documentElement: { lang: "" } };
    expect(applyDocumentLang(doc, "fr")).toBe("fr");
    expect(doc.documentElement.lang).toBe("fr");
    expect(applyDocumentLang(doc, "en")).toBe("en");
    expect(doc.documentElement.lang).toBe("en");
    expect(applyDocumentLang(doc, "xx")).toBe("en");
  });
});

describe("isEscapeKey", () => {
  test("accepts key, legacy key and keyCode forms", () => {
    expect(isEscapeKey({ key: "Escape" })).toBe(true);
    expect(isEscapeKey({ key: "Esc" })).toBe(true);
    expect(isEscapeKey({ keyCode: 27 })).toBe(true);
    expect(isEscapeKey({ key: "Enter" })).toBe(false);
    expect(isEscapeKey(null)).toBe(false);
  });
});

describe("restoreFocus", () => {
  test("focuses a connected element and ignores a detached one", () => {
    const calls = [];
    const el = { isConnected: true, focus: (o) => calls.push(o) };
    expect(restoreFocus(el)).toBe(true);
    expect(calls).toEqual([{ preventScroll: true }]);
    expect(restoreFocus({ isConnected: false, focus: () => calls.push("no") })).toBe(false);
    expect(restoreFocus(null)).toBe(false);
    expect(calls).toHaveLength(1);
  });
});

describe("zoneRowTestId", () => {
  test("names the row to hand focus back to", () => {
    expect(zoneRowTestId(8402)).toBe("poe-zone-row-8402");
    expect(zoneRowTestId(null)).toBeNull();
  });
});
