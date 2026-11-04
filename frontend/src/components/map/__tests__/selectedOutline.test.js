import { selectedOutlineRings, zoneStyle } from "../constants";

describe("selected EEZ outline", () => {
  test("Polygon: only the exterior ring, holes dropped, as [lat, lng]", () => {
    const geometry = {
      type: "Polygon",
      coordinates: [
        [[-65, 32], [-64, 32], [-64, 33], [-65, 33], [-65, 32]],
        [[-64.8, 32.3], [-64.7, 32.3], [-64.7, 32.4], [-64.8, 32.3]],
      ],
    };
    const rings = selectedOutlineRings(geometry);
    expect(rings).toHaveLength(1);
    expect(rings[0][0]).toEqual([32, -65]);
    expect(rings[0]).toHaveLength(5);
  });

  test("MultiPolygon: one exterior ring per part", () => {
    const part = (x) => [[[x, 0], [x + 1, 0], [x + 1, 1], [x, 0]], [[x + 0.2, 0.2], [x + 0.3, 0.2], [x + 0.2, 0.3], [x + 0.2, 0.2]]];
    const rings = selectedOutlineRings({ type: "MultiPolygon", coordinates: [part(0), part(5)] });
    expect(rings).toHaveLength(2);
    expect(rings[1][0]).toEqual([0, 5]);
  });

  test("the selected polygon itself draws no stroke (fill only)", () => {
    expect(zoneStyle("ia", true, 6).opacity).toBe(0);
    expect(zoneStyle("ia", true, 6).fillOpacity).toBeGreaterThan(0);
    expect(zoneStyle("ia", true, 11).fillOpacity).toBe(0);
    expect(selectedOutlineRings(null)).toEqual([]);
  });
});
