const WORLD = 360;

function value(bounds, method) {
  const result = bounds?.[method]?.();
  return Number.isFinite(result) ? result : null;
}

function quantize(valueToRound, cellDegrees, mode) {
  const scaled = valueToRound / cellDegrees;
  return (mode === "down" ? Math.floor(scaled) : Math.ceil(scaled)) * cellDegrees;
}

export function wrapViewportLongitude(lon) {
  let out = Number(lon);
  while (out > 180) out -= WORLD;
  while (out < -180) out += WORLD;
  return out;
}

/**
 * Bbox stable pendant un petit pan ; west > east représente l'antiméridien.
 * Le serveur peut alors filtrer sans renvoyer l'index mondial.
 */
export function quantizedViewportBbox(bounds, cellDegrees = 1) {
  const west = value(bounds, "getWest");
  const south = value(bounds, "getSouth");
  const east = value(bounds, "getEast");
  const north = value(bounds, "getNorth");
  if ([west, south, east, north].some((entry) => entry == null)) return null;
  if (east - west >= WORLD - cellDegrees) return "-180,-90,180,90";
  const qWest = wrapViewportLongitude(quantize(west, cellDegrees, "down"));
  const qEast = wrapViewportLongitude(quantize(east, cellDegrees, "up"));
  const qSouth = Math.max(-90, quantize(south, cellDegrees, "down"));
  const qNorth = Math.min(90, quantize(north, cellDegrees, "up"));
  return [qWest, qSouth, qEast, qNorth].join(",");
}

function lonVisible(lon, west, east) {
  for (const copy of [lon - WORLD, lon, lon + WORLD]) {
    if (copy >= west && copy <= east) return true;
  }
  return false;
}

function coordinatePairs(coords, out = []) {
  if (!Array.isArray(coords)) return out;
  if (typeof coords[0] === "number" && typeof coords[1] === "number") {
    out.push(coords);
    return out;
  }
  coords.forEach((child) => coordinatePairs(child, out));
  return out;
}

/** Conserve les entités possédant au moins un sommet dans la fenêtre visible. */
export function visibleFeatures(fc, bounds) {
  const west = value(bounds, "getWest");
  const south = value(bounds, "getSouth");
  const east = value(bounds, "getEast");
  const north = value(bounds, "getNorth");
  if ([west, south, east, north].some((entry) => entry == null)) return fc;
  return {
    ...(fc || { type: "FeatureCollection" }),
    features: (fc?.features || []).filter((feature) => coordinatePairs(
      feature?.geometry?.coordinates,
    ).some(([lon, lat]) => lat >= south && lat <= north && lonVisible(lon, west, east))),
  };
}
