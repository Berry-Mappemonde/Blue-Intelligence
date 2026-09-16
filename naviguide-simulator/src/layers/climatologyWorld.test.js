import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { climoPointLngs, cycloneLatLngCopies } from "./climatologyWorld.js";

describe("climatologyWorld antimeridian", () => {
  it("triples a Pacific rose so the +360 copy of the map is not empty", () => {
    assert.deepEqual(climoPointLngs(166.4), [166.4, 526.4, -193.6]);
    assert.deepEqual(climoPointLngs(-179.2), [-179.2, 180.8, -539.2]);
  });

  it("splits an IBTrACS track at 180° then copies the world", () => {
    const copies = cycloneLatLngCopies([
      [170, -15],
      [179, -16],
      [-179, -17],
      [-170, -18],
    ]);
    assert.equal(copies.length, 6);
    for (const part of copies) {
      assert.ok(part.length >= 2);
      for (let i = 1; i < part.length; i++) {
        assert.ok(Math.abs(part[i][1] - part[i - 1][1]) <= 180);
      }
    }
    const lngs = copies.flat().map((ll) => ll[1]);
    assert.ok(lngs.some((lng) => lng > 360));
    assert.ok(lngs.some((lng) => lng < -180));
  });
});
