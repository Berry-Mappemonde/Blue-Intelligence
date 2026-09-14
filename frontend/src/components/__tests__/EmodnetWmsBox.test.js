import { DEFAULT_SCIENCE_WMS } from "../EmodnetWmsBox";

describe("EmodnetWmsBox", () => {
  test("par défaut tout est décoché", () => {
    expect(DEFAULT_SCIENCE_WMS).toEqual({
      bathymetry: false,
      cables: false,
      substrate: false,
    });
    expect(Object.values(DEFAULT_SCIENCE_WMS).some(Boolean)).toBe(false);
  });
});
