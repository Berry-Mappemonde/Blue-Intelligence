/**
 * URL of the MapLibre worker served from public/maplibre/
 * (copied from node_modules at postinstall / prebuild).
 *
 * Webpack cannot resolve `new URL(\`./${worker}\`, import.meta.url)`
 * in the maplibre-gl bundle: the worker would not be emitted, and the
 * sea chart would look for a .mjs next to the JS chunk (404).
 */
export function maplibreWorkerUrl(publicUrl = process.env.PUBLIC_URL) {
  const base = String(publicUrl || "").replace(/\/$/, "");
  return `${base}/maplibre/maplibre-gl-worker.mjs`;
}
