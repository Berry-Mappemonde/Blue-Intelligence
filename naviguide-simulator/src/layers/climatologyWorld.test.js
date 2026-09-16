import { describe, it } from "node:test";
import assert from "node:assert/strict";
import {
  climoPointLngs,
  closeCycloneAtDateLine,
  cycloneLatLngCopies,
  groupCycloneFeatures,
  meridiansBetween,
  splitCycloneAtMeridian,
  unwrapCycloneCoords,
} from "./climatologyWorld.js";

describe("climatologyWorld antimeridian", () => {
  it("triples a Pacific rose so the +360 copy of the map is not empty", () => {
    assert.deepEqual(climoPointLngs(166.4), [166.4, 526.4, -193.6]);
    assert.deepEqual(climoPointLngs(-179.2), [-179.2, 180.8, -539.2]);
  });

  it("unwraps 179 → −179 into 179 → 181 (never the long way)", () => {
    const u = unwrapCycloneCoords([
      [170, -15],
      [179, -16],
      [-179, -17],
      [-170, -18],
    ]);
    assert.deepEqual(u, [
      [170, -15],
      [179, -16],
      [181, -17],
      [190, -18],
    ]);
  });

  it("snaps a stub that dies at 178.5° onto 180°", () => {
    const closed = closeCycloneAtDateLine([
      [153.7, 10.1],
      [178.5, 41.0],
    ]);
    assert.equal(closed[closed.length - 1][0], 180);
    assert.equal(closed[closed.length - 1][1], 41.0);
  });

  it("lists the 180° meridian between 179 and 181", () => {
    assert.deepEqual(meridiansBetween(179, 181), [180]);
    assert.deepEqual(meridiansBetween(181, 179), [180]);
    assert.deepEqual(meridiansBetween(-181, -179), [-180]);
    assert.deepEqual(meridiansBetween(170, 179), []);
  });

  it("splits a crossing track at 180° and keeps the meridian on both parts", () => {
    const parts = splitCycloneAtMeridian([
      [170, -15],
      [179, -16],
      [-179, -17],
      [-170, -18],
    ]);
    assert.equal(parts.length, 2);
    assert.equal(parts[0][parts[0].length - 1][0], 180);
    assert.equal(parts[1][0][0], 180);
    assert.ok(parts[1].some(([lon]) => lon > 180));
  });

  it("paints world copies that meet at 180°, never a 358° hop", () => {
    const copies = cycloneLatLngCopies([
      [170, -15],
      [179, -16],
      [-179, -17],
      [-170, -18],
    ]);
    assert.ok(copies.length >= 6);
    for (const part of copies) {
      assert.ok(part.length >= 2);
      for (let i = 1; i < part.length; i++) {
        assert.ok(Math.abs(part[i][1] - part[i - 1][1]) <= 180);
      }
    }
    const lngs = copies.flat().map((ll) => ll[1]);
    assert.ok(lngs.some((lng) => Math.abs(lng - 180) < 1e-6));
    assert.ok(lngs.some((lng) => lng > 360));
    assert.ok(lngs.some((lng) => lng < -180));
  });

  it("rejoins backend-split parts of the same sid before unwrap", () => {
    const groups = groupCycloneFeatures([
      { properties: { sid: "A", name: "TEST" }, geometry: { coordinates: [[170, -15], [179, -16]] } },
      { properties: { sid: "A" }, geometry: { coordinates: [[-179, -17], [-170, -18]] } },
    ]);
    assert.equal(groups.length, 1);
    const parts = splitCycloneAtMeridian(groups[0].coords);
    assert.equal(parts.length, 2);
    assert.equal(parts[0].at(-1)[0], 180);
    assert.equal(parts[1][0][0], 180);
  });
});
