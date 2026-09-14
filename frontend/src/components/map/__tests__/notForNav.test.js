import {
  NOT_FOR_NAV_STORAGE_KEY,
  disclaimerFingerprint,
  readNotForNavAccepted,
  restrictedIntentNeedsAccept,
  writeNotForNavAccepted,
} from "../notForNav";

function memStore() {
  const bag = {};
  return {
    getItem: (k) => (k in bag ? bag[k] : null),
    setItem: (k, v) => { bag[k] = String(v); },
  };
}

describe("notForNav", () => {
  test("sans acceptation, mer / WMS / overlay / satellite demandent un clic", () => {
    expect(restrictedIntentNeedsAccept(false, { basemap: "sea" })).toBe(true);
    expect(restrictedIntentNeedsAccept(false, { overlay: true })).toBe(true);
    expect(restrictedIntentNeedsAccept(false, { wms: { bathymetry: true } })).toBe(true);
    expect(restrictedIntentNeedsAccept(false, { satellite: true })).toBe(true);
    expect(restrictedIntentNeedsAccept(false, { basemap: "dark", overlay: false })).toBe(false);
    expect(restrictedIntentNeedsAccept(true, { basemap: "sea" })).toBe(false);
  });

  test("persiste version + empreinte ; un nouveau texte redemande", () => {
    const store = memStore();
    writeNotForNavAccepted(store, "Not for navigation", "body v1");
    expect(readNotForNavAccepted(store, "Not for navigation", "body v1")).toBe(true);
    expect(readNotForNavAccepted(store, "Not for navigation", "body v2")).toBe(false);
    expect(store.getItem(NOT_FOR_NAV_STORAGE_KEY)).toContain("textKey");
    expect(disclaimerFingerprint("a", "b")).not.toBe(disclaimerFingerprint("a", "c"));
  });
});
