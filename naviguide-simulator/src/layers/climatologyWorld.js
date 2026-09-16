import { unwrapLon, worldCopyCoords } from "../utils/geo.js";
import { worldCopyLngs } from "../utils/gribSymbols.js";

/** Snap an endpoint onto ±180 if it already sits next to the date line. */
const DATE_LINE_SNAP_DEG = 8;

/**
 * Trois longitudes (0 / +360 / −360) pour que l’atlas tienne
 * sur la copie Pacifique près de 180°, pas seulement sur [-180, 180].
 */
export function climoPointLngs(lon) {
  return worldCopyLngs(lon);
}

function isLonLat(c) {
  return Array.isArray(c) && c.length >= 2 && Number.isFinite(Number(c[0])) && Number.isFinite(Number(c[1]));
}

/** Unwrap so 179 → −179 becomes 179 → 181 (short path, never the long way). */
export function unwrapCycloneCoords(coordinates) {
  const out = [];
  for (const c of coordinates || []) {
    if (!isLonLat(c)) continue;
    const lon = Number(c[0]);
    const lat = Number(c[1]);
    if (!out.length) out.push([lon, lat]);
    else out.push([unwrapLon(out[out.length - 1][0], lon), lat]);
  }
  return out;
}

function snapToDateLine(lon) {
  const x = Number(lon);
  if (!Number.isFinite(x)) return null;
  const n = ((x + 180) % 360 + 360) % 360 - 180;
  if (n > 180 - DATE_LINE_SNAP_DEG) return 180;
  if (n < -180 + DATE_LINE_SNAP_DEG) return -180;
  return null;
}

/** Prolong a stub that dies at 178° / −178° onto the meridian so copies meet. */
export function closeCycloneAtDateLine(coordinates) {
  const pts = (coordinates || []).filter(isLonLat).map((c) => [Number(c[0]), Number(c[1])]);
  if (pts.length < 2) return pts;
  const out = pts.slice();
  const first = out[0];
  const last = out[out.length - 1];
  const s0 = snapToDateLine(first[0]);
  const s1 = snapToDateLine(last[0]);
  if (s0 != null && s0 !== first[0]) out.unshift([s0, first[1]]);
  if (s1 != null && s1 !== last[0]) out.push([s1, last[1]]);
  return out;
}

/** Meridians 180 + 360k strictly between x0 and x1. */
export function meridiansBetween(x0, x1) {
  const a = Number(x0);
  const b = Number(x1);
  if (!Number.isFinite(a) || !Number.isFinite(b) || a === b) return [];
  const lo = Math.min(a, b);
  const hi = Math.max(a, b);
  const found = [];
  let k = Math.ceil((lo - 180) / 360);
  for (;;) {
    const m = 180 + 360 * k;
    if (m >= hi) break;
    if (m > lo) found.push(m);
    k += 1;
    if (found.length > 8) break;
  }
  return a < b ? found : found.slice().reverse();
}

function interpLat(x0, y0, x1, y1, x) {
  const d = x1 - x0;
  if (d === 0) return y1;
  return y0 + (y1 - y0) * ((x - x0) / d);
}

/**
 * Unwrap, then cut at every 180° + 360k crossing.
 * Both sides get the interpolated meridian point (no hole, no grand tour).
 */
export function splitCycloneAtMeridian(coordinates) {
  const u = unwrapCycloneCoords(closeCycloneAtDateLine(coordinates));
  if (u.length < 2) return u.length ? [u] : [];
  const parts = [];
  let cur = [u[0]];
  for (let i = 1; i < u.length; i++) {
    const [x0, y0] = cur[cur.length - 1];
    const [x1, y1] = u[i];
    const cuts = meridiansBetween(x0, x1);
    if (!cuts.length) {
      cur.push([x1, y1]);
      continue;
    }
    let px = x0;
    let py = y0;
    for (const m of cuts) {
      const y = interpLat(px, py, x1, y1, m);
      cur.push([m, y]);
      if (cur.length >= 2) parts.push(cur);
      cur = [[m, y]];
      px = m;
      py = y;
    }
    cur.push([x1, y1]);
  }
  if (cur.length >= 2) parts.push(cur);
  return parts.filter((p) => p.length >= 2);
}

/**
 * Trace IBTrACS : unwrap + coupe à 180°, puis copies ±360°.
 * Entrée GeoJSON [lon, lat][]. Sortie Leaflet [lat, lng][][].
 */
export function cycloneLatLngCopies(coordinates) {
  const parts = splitCycloneAtMeridian(coordinates);
  const copies = [];
  for (const part of parts) {
    for (const copy of worldCopyCoords(part)) {
      copies.push(copy.map(([lon, lat]) => [lat, lon]));
    }
  }
  return copies;
}

/** Backend may emit several LineStrings for one sid. Reassemble in order. */
export function groupCycloneFeatures(features) {
  const groups = [];
  const index = new Map();
  for (const f of features || []) {
    const coords = f?.geometry?.coordinates;
    if (!Array.isArray(coords) || coords.length < 2) continue;
    const sid = f?.properties?.sid;
    if (sid && index.has(sid)) {
      index.get(sid).coords.push(...coords);
      continue;
    }
    const g = { properties: f.properties || {}, coords: coords.slice() };
    groups.push(g);
    if (sid) index.set(sid, g);
  }
  return groups;
}
