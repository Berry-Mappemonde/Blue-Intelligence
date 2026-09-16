import { useEffect, useMemo, useRef, useState } from "react";
import { haversineNm, wrapLon } from "../utils/geo.js";
import {
  boatPositionFromCast,
  emptyDossier,
  mergeDossier,
  zeeEnterEvent,
} from "../engine/ici.js";
import { narrateIci } from "../engine/iciBriefing.js";

const API_URL = import.meta.env.VITE_API_URL ?? "";
const DEBOUNCE_MS = 800;
const MOVE_NM = 3;
const FETCH_MS = 40000;
const SCHEDULER_MS = 1000;

/**
 * Fill the `ici()` bag around the boat and turn it into a story.
 * One step = one GET /ici. No chat, no Tavily.
 */
export function useIciDossier({
  enabled,
  cast,
  snappedPosition,
  polarMeta,
  jambe,
  lang = "fr",
  month,
  destLat,
  destLon,
  climatology,
}) {
  const [remote, setRemote] = useState(null);
  const lastFetchRef = useRef(null);
  const prevZeeRef = useRef(undefined);
  const abortRef = useRef(null);
  const timerRef = useRef(null);
  const requestedRef = useRef(null);
  const boat = boatPositionFromCast(cast, snappedPosition);

  useEffect(() => {
    requestedRef.current = boat
      ? { lat: boat.lat, lon: boat.lon, month, destLat, destLon }
      : null;
  }, [boat?.lat, boat?.lon, month, destLat, destLon]);

  useEffect(() => {
    if (!enabled) {
      setRemote(null);
      lastFetchRef.current = null;
      prevZeeRef.current = undefined;
      abortRef.current?.abort();
      abortRef.current = null;
      clearTimeout(timerRef.current);
      return undefined;
    }

    let disposed = false;
    const schedule = () => {
      const target = requestedRef.current;
      if (!target || abortRef.current) return;
      const lat = target.lat;
      const lon = wrapLon(target.lon);
      const now = Date.now();
      const last = lastFetchRef.current;
      if (
        last
        && haversineNm(last.lat, last.lon, lat, lon) < MOVE_NM
        && last.month === target.month
        && last.destLat === target.destLat
        && last.destLon === target.destLon
        && now - last.at < FETCH_MS
      ) return;

      // Marque l'échantillon avant le debounce : un playhead à 8 Hz ne peut
      // plus réarmer indéfiniment le même timeout.
      lastFetchRef.current = {
        lat,
        lon,
        month: target.month,
        destLat: target.destLat,
        destLon: target.destLon,
        at: now,
      };
      clearTimeout(timerRef.current);
      timerRef.current = setTimeout(() => {
        if (disposed) return;
        const ctrl = new AbortController();
        abortRef.current = ctrl;
        const kill = setTimeout(() => ctrl.abort(), FETCH_MS);
        const q = new URLSearchParams({ lat: String(lat), lon: String(lon) });
        if (Number.isFinite(Number(target.month))) q.set("month", String(target.month));
        if (Number.isFinite(Number(target.destLat)) && Number.isFinite(Number(target.destLon))) {
          q.set("dest_lat", String(target.destLat));
          q.set("dest_lon", String(target.destLon));
        }
        fetch(`${API_URL}/ici?${q.toString()}`, {
          signal: ctrl.signal,
        })
          .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`ici ${r.status}`))))
          .then((data) => {
            const event = zeeEnterEvent(prevZeeRef.current, data?.zee);
            prevZeeRef.current = data?.zee?.mrgid ?? null;
            setRemote({ ...data, event });
          })
          .catch(() => {
            if (ctrl.signal.aborted && disposed) return;
            setRemote({
              ...emptyDossier(lat, lon),
              sources: { zee: "error", bi: "unavailable" },
            });
          })
          .finally(() => {
            clearTimeout(kill);
            if (abortRef.current === ctrl) abortRef.current = null;
          });
      }, DEBOUNCE_MS);
    };

    schedule();
    const scheduler = setInterval(schedule, SCHEDULER_MS);
    return () => {
      disposed = true;
      clearInterval(scheduler);
      clearTimeout(timerRef.current);
      abortRef.current?.abort();
      abortRef.current = null;
    };
  }, [enabled, month, destLat, destLon]);

  useEffect(() => {
    if (!enabled || boat) return undefined;
    setRemote(null);
    lastFetchRef.current = null;
    prevZeeRef.current = undefined;
    abortRef.current?.abort();
    abortRef.current = null;
    clearTimeout(timerRef.current);
    return undefined;
  }, [enabled, boat]);

  const dossier = useMemo(() => {
    if (!enabled || !boat || !remote) return null;
    return mergeDossier(remote, {
      polarMeta,
      jambe,
      event: remote.event,
      climatology: remote.climatology || climatology || null,
    });
  }, [enabled, boat, remote, polarMeta, jambe, climatology]);

  const briefing = useMemo(
    () => (dossier ? narrateIci(dossier, lang) : ""),
    [dossier, lang],
  );

  return { dossier, briefing, loading: Boolean(enabled && boat && !remote) };
}
