import { cycloneLatLngCopies, groupCycloneFeatures, unwrapCycloneCoords } from "../cycloneTracks";

describe("cycloneTracks antimeridian", () => {
  test("unwraps 179 → −179 into 179 → 181", () => {
    expect(unwrapCycloneCoords([
      [170, -15], [179, -16], [-179, -17], [-170, -18],
    ])).toEqual([
      [170, -15], [179, -16], [181, -17], [190, -18],
    ]);
  });

  test("keeps one continuous polyline, never a cut at 180°", () => {
    const copies = cycloneLatLngCopies([
      [170, -15], [179, -16], [-179, -17], [-170, -18],
    ]);
    expect(copies).toHaveLength(3);
    const [base, plus, minus] = copies;
    expect(base.map((ll) => ll[1])).toEqual([170, 179, 181, 190]);
    expect(plus.map((ll) => ll[1])).toEqual([530, 539, 541, 550]);
    expect(minus.map((ll) => ll[1])).toEqual([-190, -181, -179, -170]);
    for (const part of copies) {
      for (let i = 1; i < part.length; i++) {
        expect(Math.abs(part[i][1] - part[i - 1][1])).toBeLessThanOrEqual(180);
      }
    }
  });

  test("rejoins split sid parts then unwraps to 170 → 190", () => {
    const groups = groupCycloneFeatures([
      { properties: { sid: "A", name: "TEST" }, geometry: { coordinates: [[170, -15], [179, -16]] } },
      { properties: { sid: "A" }, geometry: { coordinates: [[-179, -17], [-170, -18]] } },
    ]);
    expect(groups).toHaveLength(1);
    expect(unwrapCycloneCoords(groups[0].coords)).toEqual([
      [170, -15], [179, -16], [181, -17], [190, -18],
    ]);
  });
});
