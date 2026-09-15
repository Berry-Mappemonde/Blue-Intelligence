/** Couloir bateau seulement — refuse un bbox globe. */
export function corridorBboxOk(bbox) {
  if (!bbox || bbox.length !== 4) return false;
  const [south, north, west, east] = bbox.map(Number);
  if (![south, north, west, east].every(Number.isFinite)) return false;
  return north - south <= 20 && Math.abs(east - west) <= 40;
}
