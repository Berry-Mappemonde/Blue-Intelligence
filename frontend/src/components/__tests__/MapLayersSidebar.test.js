import { DEFAULT_SCIENCE_WMS } from "../MapLayersSidebar";

describe("MapLayersSidebar", () => {
  test("EMODnet est tout décoché par défaut", () => {
    expect(DEFAULT_SCIENCE_WMS).toEqual({
      bathymetry: false,
      cables: false,
      substrate: false,
    });
    expect(Object.values(DEFAULT_SCIENCE_WMS).some(Boolean)).toBe(false);
  });
});
