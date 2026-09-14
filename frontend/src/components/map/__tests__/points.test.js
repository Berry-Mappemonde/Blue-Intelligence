import { penRadius, POPUP_OPTS } from "../points";

describe("map dots", () => {
  test("the Bic-point radius grows with zoom", () => {
    expect(penRadius(2)).toBeLessThan(penRadius(8));
    expect(penRadius(8)).toBeLessThan(penRadius(14));
    expect(penRadius(2)).toBeLessThan(2);
  });

  test("popups do not move the map", () => {
    expect(POPUP_OPTS.autoPan).toBe(false);
  });
});
