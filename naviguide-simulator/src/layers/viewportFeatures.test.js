import { describe, it } from "node:test";
import assert from "node:assert/strict";
import {
  quantizedViewportBbox,
  visibleFeatures,
  wrapViewportLongitude,
} from "./viewportFeatures.js";

function bounds(west, south, east, north) {
  return {
    getWest: () => west,
    getSouth: () => south,
    getEast: () => east,
    getNorth: () => north,
  };
}

describe("viewportFeatures", () => {
  it("coalesce un petit pan dans la même bbox", () => {
    assert.equal(
      quantizedViewportBbox(bounds(-5.8, 42.1, -3.2, 44.4)),
      "-6,42,-3,45",
    );
    assert.equal(
      quantizedViewportBbox(bounds(-5.2, 42.3, -3.1, 44.1)),
      "-6,42,-3,45",
    );
  });

  it("préserve une bbox qui traverse l’antiméridien", () => {
    assert.equal(quantizedViewportBbox(bounds(179.2, -3.1, 181.4, 2.2)), "179,-4,-178,3");
    assert.equal(wrapViewportLongitude(540), 180);
  });

  it("écarte les points hors viewport et garde la copie monde visible", () => {
    const fc = {
      type: "FeatureCollection",
      features: [
        { type: "Feature", geometry: { type: "Point", coordinates: [174, -20] }, properties: { name: "Fidji" } },
        { type: "Feature", geometry: { type: "Point", coordinates: [0, 0] }, properties: { name: "Greenwich" } },
      ],
    };
    const visible = visibleFeatures(fc, bounds(-190, -30, -170, -10));
    assert.deepEqual(visible.features.map((feature) => feature.properties.name), ["Fidji"]);
  });
});
