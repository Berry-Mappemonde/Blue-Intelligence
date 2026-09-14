/**
 * Cache the run list per mode — one fetch, reused each time the selector
 * opens. Invalidated when a run is launched from the Console, and
 * refreshed on its own after MAX_AGE_MS (done/failed states catch up).
 */

const MAX_AGE_MS = 5 * 60 * 1000;

const cache = new Map();
const inflight = new Map();

export function fetchRunsOnce(mode, loader) {
  const hit = cache.get(mode);
  if (hit && Date.now() - hit.at < MAX_AGE_MS) return Promise.resolve(hit.items);
  if (inflight.has(mode)) return inflight.get(mode);
  const pending = Promise.resolve()
    .then(loader)
    .then((items) => {
      cache.set(mode, { at: Date.now(), items: items || [] });
      inflight.delete(mode);
      return items || [];
    })
    .catch((err) => {
      inflight.delete(mode);
      throw err;
    });
  inflight.set(mode, pending);
  return pending;
}

export function invalidateRuns(mode) {
  if (mode) cache.delete(mode);
  else cache.clear();
}
