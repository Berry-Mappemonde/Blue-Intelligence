import axios from "axios";

// Backend URL: REACT_APP_BACKEND_URL when set, otherwise same-origin
// (the CRA proxy routes /api to localhost:8001 in dev; in production the
// reverse proxy serves /api/* — see README).
export const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "";

// ---------------------------------------------------------------------------
// Admin mode — opening the app with `?admin=<key>` stores the key (localStorage)
// and then sends it in the X-Admin-Key header; `?admin=off` clears it.
// Console / Review tabs only appear once the backend validates the key
// (GET /admin/check). The query param is stripped from the URL after reading.
// ---------------------------------------------------------------------------
const ADMIN_STORAGE_KEY = "bi.adminKey";

function bootstrapAdminKey() {
  try {
    const params = new URLSearchParams(window.location.search);
    const fromUrl = params.get("admin");
    if (fromUrl !== null) {
      if (fromUrl === "" || fromUrl === "off") {
        localStorage.removeItem(ADMIN_STORAGE_KEY);
      } else {
        localStorage.setItem(ADMIN_STORAGE_KEY, fromUrl);
      }
      params.delete("admin");
      const qs = params.toString();
      window.history.replaceState(
        {}, "",
        window.location.pathname + (qs ? `?${qs}` : "") + window.location.hash,
      );
    }
    return localStorage.getItem(ADMIN_STORAGE_KEY) || "";
  } catch (_) {
    return "";
  }
}

const adminKey = bootstrapAdminKey();

export function hasAdminKey() {
  return Boolean(adminKey);
}

export function clearAdminKey() {
  try { localStorage.removeItem(ADMIN_STORAGE_KEY); } catch (_) { /* ignore */ }
}

const api = axios.create({
  baseURL: `${BACKEND_URL}/api`,
  timeout: 120000,
  ...(adminKey ? { headers: { "X-Admin-Key": adminKey } } : {}),
});

export default api;
