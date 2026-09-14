import L from "leaflet";
import { computePopupFit, POPUP_FIT_PAD } from "../popupFit";
import { POPUP_OPTS } from "../points";

describe("popup display policy", () => {
  test("popups do not move the map", () => {
    expect(POPUP_OPTS.autoPan).toBe(false);
    expect(POPUP_OPTS.keepInView).toBe(false);
  });

  test("Leaflet repositions via the policy (no more wrapper translate)", () => {
    expect(L.Popup.prototype._updatePosition.name).toBe("patchedPopupPosition");
  });

  test("at the centre, the popup stays above and centred", () => {
    const fit = computePopupFit({
      mapW: 1000, mapH: 700, anchorX: 500, anchorY: 400,
      popupW: 340, popupH: 280,
    });
    expect(fit.placeBelow).toBe(false);
    expect(fit.left).toBeCloseTo(500 - 340 / 2, 5);
    expect(Math.abs(fit.tipShift)).toBeLessThan(1);
    expect(fit.maxHeight).toBe(280);
  });

  test("too close to the top, the popup flips below", () => {
    const fit = computePopupFit({
      mapW: 1000, mapH: 700, anchorX: 500, anchorY: 80,
      popupW: 340, popupH: 420,
    });
    expect(fit.placeBelow).toBe(true);
    expect(fit.maxHeight).toBeGreaterThan(300);
    expect(fit.maxHeight).toBeLessThanOrEqual(700 - POPUP_FIT_PAD * 2);
  });

  test("a small popup near the top stays above if it fits", () => {
    const fit = computePopupFit({
      mapW: 1000, mapH: 700, anchorX: 500, anchorY: 80,
      popupW: 220, popupH: 40,
    });
    expect(fit.placeBelow).toBe(false);
  });

  test("too close to the right, the box slides left and the tip follows", () => {
    const fit = computePopupFit({
      mapW: 1000, mapH: 700, anchorX: 960, anchorY: 400,
      popupW: 340, popupH: 200,
    });
    expect(fit.placeBelow).toBe(false);
    expect(fit.left + fit.width).toBeLessThanOrEqual(1000 - POPUP_FIT_PAD);
    expect(fit.left).toBeGreaterThanOrEqual(POPUP_FIT_PAD);
    expect(fit.tipShift).toBeGreaterThan(0);
  });

  test("too close to the left, the box stays inside the map", () => {
    const fit = computePopupFit({
      mapW: 1000, mapH: 700, anchorX: 40, anchorY: 400,
      popupW: 340, popupH: 200,
    });
    expect(fit.left).toBe(POPUP_FIT_PAD);
    expect(fit.tipShift).toBeLessThan(0);
  });

  test("Tunisia case (top-right): below + left shift, fully inside the map", () => {
    const fit = computePopupFit({
      mapW: 1000, mapH: 700, anchorX: 850, anchorY: 120,
      popupW: 340, popupH: 420,
    });
    expect(fit.placeBelow).toBe(true);
    expect(fit.left).toBeGreaterThanOrEqual(POPUP_FIT_PAD);
    expect(fit.left + fit.width).toBeLessThanOrEqual(1000 - POPUP_FIT_PAD);
    expect(fit.height).toBeLessThanOrEqual(fit.maxHeight);
    expect(fit.maxHeight).toBeLessThanOrEqual(700 - POPUP_FIT_PAD * 2);
  });

  test("a popup wider than the map is clamped to the bounds", () => {
    const fit = computePopupFit({
      mapW: 320, mapH: 500, anchorX: 160, anchorY: 250,
      popupW: 400, popupH: 180,
    });
    expect(fit.width).toBe(320 - POPUP_FIT_PAD * 2);
    expect(fit.maxWidth).toBe(320 - POPUP_FIT_PAD * 2);
    expect(fit.left).toBe(POPUP_FIT_PAD);
  });

  test("a popup taller than the map is capped", () => {
    const fit = computePopupFit({
      mapW: 800, mapH: 400, anchorX: 400, anchorY: 200,
      popupW: 300, popupH: 900,
    });
    expect(fit.maxHeight).toBeLessThanOrEqual(400 - POPUP_FIT_PAD * 2);
    expect(fit.maxHeight).toBeGreaterThanOrEqual(80);
  });

  test("in the middle, a large popup shrinks above rather than flipping", () => {
    const fit = computePopupFit({
      mapW: 1000, mapH: 700, anchorX: 500, anchorY: 350,
      popupW: 340, popupH: 420,
    });
    expect(fit.placeBelow).toBe(false);
    expect(fit.maxHeight).toBeLessThan(420);
    expect(fit.maxHeight).toBeGreaterThan(200);
  });
});
