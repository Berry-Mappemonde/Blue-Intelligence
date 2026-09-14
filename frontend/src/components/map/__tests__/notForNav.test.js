import {
  NOT_FOR_NAV_STORAGE_KEY,
  disclaimerFingerprint,
  readNotForNavAccepted,
  siteEntryNeedsAccept,
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
  test("without acceptance, the site stays closed", () => {
    expect(siteEntryNeedsAccept(false)).toBe(true);
    expect(siteEntryNeedsAccept(true)).toBe(false);
  });

  test("persists version + fingerprint; a new text asks again", () => {
    const store = memStore();
    writeNotForNavAccepted(store, "This map is not for navigating", "body v1");
    expect(readNotForNavAccepted(store, "This map is not for navigating", "body v1")).toBe(true);
    expect(readNotForNavAccepted(store, "This map is not for navigating", "body v2")).toBe(false);
    expect(store.getItem(NOT_FOR_NAV_STORAGE_KEY)).toContain("textKey");
    expect(disclaimerFingerprint("a", "b")).not.toBe(disclaimerFingerprint("a", "c"));
  });
});
