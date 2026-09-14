import {
  DEFAULT_SAFETY_M,
  SAFETY_ISOBATH_LAYER_ID,
  safetyIsobathLayers,
} from "../safetyIsobathSpec";

describe("safetyIsobathSpec", () => {
  test("DEPARE fill where drval1 < threshold (default 2 m)", () => {
    const [layer] = safetyIsobathLayers();
    expect(layer.id).toBe(SAFETY_ISOBATH_LAYER_ID);
    expect(layer.source).toBe("seascape-vector");
    expect(layer["source-layer"]).toBe("depare");
    expect(layer.filter).toEqual([
      "all",
      ["has", "drval1"],
      ["<", ["to-number", ["get", "drval1"]], DEFAULT_SAFETY_M],
    ]);
  });

  test("5 / 10 m threshold; unknown value → 2 m", () => {
    expect(safetyIsobathLayers(5)[0].filter[2][2]).toBe(5);
    expect(safetyIsobathLayers(10)[0].filter[2][2]).toBe(10);
    expect(safetyIsobathLayers(99)[0].filter[2][2]).toBe(DEFAULT_SAFETY_M);
  });
});
