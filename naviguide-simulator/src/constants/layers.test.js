import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { ALL_LAYER_CONFIG, DEFAULT_SHOW_ZEE } from "./layers.js";

describe("ALL_LAYER_CONFIG", () => {
  it("replaces Science with the 8 charts, without a single chip", () => {
    const keys = ALL_LAYER_CONFIG.map((c) => c.key);
    assert.deepEqual(keys, [
      "zee", "wpi", "balisage", "projects", "marinas",
      "capitaineries", "poe", "amp",
      "sextant", "argo", "odatis", "edmed", "csr",
      "bathymetry", "fonds", "cables",
      "climatology",
    ]);
    assert.equal(keys.includes("science"), false);
  });

  it("ZEE off au premier pixel", () => {
    assert.equal(DEFAULT_SHOW_ZEE, false);
  });
});
