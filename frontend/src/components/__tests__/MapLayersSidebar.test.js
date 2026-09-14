import { DEFAULT_SCIENCE_WMS } from "../MapLayersSidebar";

describe("MapLayersSidebar", () => {
  test("EMODnet is all unchecked by default", () => {
    expect(DEFAULT_SCIENCE_WMS).toEqual({
      bathymetry: false,
      cables: false,
      substrate: false,
    });
    expect(Object.values(DEFAULT_SCIENCE_WMS).some(Boolean)).toBe(false);
  });
});
