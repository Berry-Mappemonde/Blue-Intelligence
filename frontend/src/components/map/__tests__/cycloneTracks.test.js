import { cycloneLatLngCopies, splitCycloneAtMeridian, unwrapCycloneCoords } from "../cycloneTracks";

describe("cycloneTracks antimeridian", () => {
  test("unwraps 179 → −179 into 179 → 181", () => {
    expect(unwrapCycloneCoords([
      [170, -15], [179, -16], [-179, -17], [-170, -18],
    ])).toEqual([
      [170, -15], [179, -16], [181, -17], [190, -18],
    ]);
  });

  test("splits at 180° and keeps the meridian on both parts", () => {
    const parts = splitCycloneAtMeridian([
      [170, -15], [179, -16], [-179, -17], [-170, -18],
    ]);
    expect(parts).toHaveLength(2);
    expect(parts[0][parts[0].length - 1][0]).toBe(180);
    expect(parts[1][0][0]).toBe(180);
  });

  test("Leaflet copies never hop more than 180° of longitude", () => {
    const copies = cycloneLatLngCopies([
      [170, -15], [179, -16], [-179, -17], [-170, -18],
    ]);
    expect(copies.length).toBeGreaterThanOrEqual(6);
    for (const part of copies) {
      for (let i = 1; i < part.length; i++) {
        expect(Math.abs(part[i][1] - part[i - 1][1])).toBeLessThanOrEqual(180);
      }
    }
    const lngs = copies.flat().map((ll) => ll[1]);
    expect(lngs.some((lng) => Math.abs(lng - 180) < 1e-6)).toBe(true);
  });
});
