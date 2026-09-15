import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { corridorBboxOk } from "./gribCorridor.js";

describe("couloir GRIB", () => {
  it("accepte un rectangle bateau, refuse un globe", () => {
    assert.equal(corridorBboxOk([10, 16, -65, -58]), true);
    assert.equal(corridorBboxOk([-80, 80, -180, 180]), false);
    assert.equal(corridorBboxOk(null), false);
  });
});
