import { splitAntimeridianCoords, worldCopyParts } from "../utils/geo.js";
import { worldCopyLngs } from "../utils/gribSymbols.js";

/**
 * Trois longitudes (0 / +360 / −360) pour que l’atlas tienne
 * sur la copie Pacifique près de 180°, pas seulement sur [-180, 180].
 */
export function climoPointLngs(lon) {
  return worldCopyLngs(lon);
}

/**
 * Trace IBTrACS : coupe à ±180°, puis copie ±360°.
 * Entrée GeoJSON [lon, lat][]. Sortie Leaflet [lat, lng][][].
 */
export function cycloneLatLngCopies(coordinates) {
  const lonLat = (coordinates || []).filter((c) => Array.isArray(c) && c.length >= 2);
  const parts = splitAntimeridianCoords(lonLat);
  return worldCopyParts(parts).map((part) => part.map(([lon, lat]) => [lat, lon]));
}
