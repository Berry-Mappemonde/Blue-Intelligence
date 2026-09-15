import { shouldShowBiOverlay } from "../useBiOverlay";

describe("shouldShowBiOverlay", () => {
  test("stays on for projects when the user left the overlay enabled", () => {
    expect(shouldShowBiOverlay({
      overlayOn: true, nauticalAllowed: true, mode: "projects",
    })).toBe(true);
  });

  test("turns off in climatology so July Hs and cyclone tracks can paint", () => {
    expect(shouldShowBiOverlay({
      overlayOn: true, nauticalAllowed: true, mode: "climatology",
    })).toBe(false);
  });

  test("stays off when the overlay toggle or nautical consent is off", () => {
    expect(shouldShowBiOverlay({
      overlayOn: false, nauticalAllowed: true, mode: "projects",
    })).toBe(false);
    expect(shouldShowBiOverlay({
      overlayOn: true, nauticalAllowed: false, mode: "projects",
    })).toBe(false);
  });
});
