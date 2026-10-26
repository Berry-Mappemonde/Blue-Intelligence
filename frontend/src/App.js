import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import api, { verifyZonePoe, hasAdminKey } from "./api";
import { makeT } from "./i18n";
import { mergeVerifyIntoFiche } from "./components/poeRegistry";
import Header from "./components/Header";
import SwarmPanel from "./components/SwarmPanel";
import MarinasPanel from "./components/MarinasPanel";
import CapitaineriesPanel from "./components/CapitaineriesPanel";
import FormalitiesPanel from "./components/FormalitiesPanel";
import AmpPanel from "./components/AmpPanel";
import SciencePanel from "./components/SciencePanel";
import ClimatologyPanel from "./components/ClimatologyPanel";
import MapView from "./components/MapView";
import AuditView from "./components/AuditView";
import ReviewView from "./components/ReviewView";
import SettingsPanel from "./components/SettingsPanel";
import ReportModal from "./components/ReportModal";
import NotForNavModal from "./components/map/NotForNavModal";
import { DEFAULT_SCIENCE_WMS } from "./components/MapLayersSidebar";
import { DEFAULT_SAFETY_M } from "./components/map/safetyIsobathSpec";
import {
  readNotForNavAccepted,
  siteEntryNeedsAccept,
  writeNotForNavAccepted,
} from "./components/map/notForNav";

const RUNS_LIST_EP = {
  projects: "/projects/runs",
  marinas: "/marinas/runs",
  capitaineries: "/capitaineries/runs",
  amp: "/amp/runs",
};

function latLngsFromFc(fc) {
  const pts = [];
  const pushPos = (c) => {
    if (Array.isArray(c) && typeof c[0] === "number" && typeof c[1] === "number") {
      pts.push([c[1], c[0]]);
      return;
    }
    if (Array.isArray(c)) c.forEach(pushPos);
  };
  for (const f of fc?.features || []) {
    if (f?.geometry?.coordinates) pushPos(f.geometry.coordinates);
  }
  return pts;
}

// Heavy datasets displayed only by one mode — fetched when that mode opens.
const MODE_DATASETS = {
  marinas: ["marinas", "anchorages"],
  capitaineries: ["capitaineries"],
  formalities: ["poeZones", "poePorts"],
  science: ["science"],
};

const MODES = ["projects", "marinas", "capitaineries", "formalities", "amp", "science", "climatology"];

// Read the persisted mode on boot. Default = "projects". (7 modes)
const readInitialMode = () => {
  try {
    const fromUrl = new URLSearchParams(window.location.search).get("mode");
    if (MODES.includes(fromUrl)) return fromUrl;
    const v = localStorage.getItem("bi.mode");
    if (MODES.includes(v)) return v;
  } catch (_) {
    /* localStorage disabled */
  }
  return "projects";
};

const readInitialLang = () => {
  try {
    const v = localStorage.getItem("bi.lang");
    if (v === "fr" || v === "en") return v;
  } catch (_) { /* disabled */ }
  return "fr";
};

const readInitialBasemap = () => {
  try {
    const v = localStorage.getItem("bi.basemap");
    if (v === "dark" || v === "light" || v === "sea") return v;
  } catch (_) { /* disabled */ }
  return "sea";
};

export default function App() {
  const [lang, setLangRaw] = useState(readInitialLang);
  const setLang = useCallback((l) => {
    setLangRaw(l);
    try { localStorage.setItem("bi.lang", l); } catch (_) { /* ignore */ }
  }, []);
  const [view, setView] = useState("map");
  // Admin mode — déterminé par GET /admin/check (ouvert par défaut en local sans ADMIN_KEY).
  const [isAdmin, setIsAdmin] = useState(false);
  const [adminChecked, setAdminChecked] = useState(false);
  const [mode, setModeRaw] = useState(readInitialMode());   // 7 modes incl. climatology
  const [showSettings, setShowSettings] = useState(false);
  const [status, setStatus] = useState(null);
  const [projects, setProjects] = useState({ type: "FeatureCollection", features: [] });
  const [funders, setFunders] = useState({ total: 0, funders: [] });
  const [funderFilter, setFunderFilter] = useState("All");
  const [searchQuery, setSearchQuery] = useState("");
  const [basemap, setBasemapRaw] = useState(readInitialBasemap);
  const setBasemap = useCallback((v) => {
    setBasemapRaw(v);
    try { localStorage.setItem("bi.basemap", v); } catch (_) { /* ignore */ }
  }, []);
  const [scienceSourceFilter, setScienceSourceFilter] = useState("argo");
  const [overlayOn, setOverlayOn] = useState(true);
  const [showReview, setShowReviewRaw] = useState(false);
  const showReviewRef = useRef(false);
  const setShowReview = useCallback((v) => {
    const on = !!v;
    showReviewRef.current = on;
    setShowReviewRaw(on);
  }, []);
  const [notForNavOk, setNotForNavOk] = useState(() => {
    const t0 = makeT(readInitialLang());
    return readNotForNavAccepted(
      undefined, t0("notForNavTitle"), t0("notForNavBody"),
    );
  });
  const [ampLfpFilter, setAmpLfpFilter] = useState("All");
  const [flyToProject, setFlyToProject] = useState(null);
  const [settings, setSettings] = useState(null);
  const [showReport, setShowReport] = useState(false);
  const [categories, setCategories] = useState([]);
  const [categoryFilter, setCategoryFilter] = useState("All");
  const [marinas, setMarinas] = useState({ type: "FeatureCollection", features: [] });
  const [flyToMarina, setFlyToMarina] = useState(null); // {id, lat, lon} used as a one-shot signal
  const [capitaineries, setCapitaineries] = useState({ type: "FeatureCollection", features: [] });
  const [flyToCapitainerie, setFlyToCapitainerie] = useState(null);
  // Science mode — ocean catalogues + Argo floats
  const [science, setScience] = useState({ type: "FeatureCollection", features: [] });
  const [flyToScience, setFlyToScience] = useState(null);
  const [scienceWms, setScienceWms] = useState(() => ({ ...DEFAULT_SCIENCE_WMS }));
  const toggleScienceWms = useCallback((id, on) => {
    setScienceWms((prev) => ({ ...prev, [id]: !!on }));
  }, []);
  const [safetyM, setSafetyM] = useState(DEFAULT_SAFETY_M);
  const [noaaAidsOn, setNoaaAidsOn] = useState(false);
  const [climoMonth, setClimoMonth] = useState(() => new Date().getMonth() + 1);
  const [climoFilters, setClimoFilters] = useState(() => {
    try {
      const only = new URLSearchParams(window.location.search).get("climo");
      if (only) {
        const parts = only.toLowerCase().split(/[,+\s]+/);
        return {
          wind: parts.includes("wind"),
          wave: parts.includes("wave"),
          current: parts.includes("current"),
          cyclones: parts.includes("cyclones"),
        };
      }
      const raw = localStorage.getItem("bi.climoFilters.v2");
      if (raw) return { wind: true, wave: true, current: true, cyclones: true, ...JSON.parse(raw) };
    } catch (_) { /* ignore */ }
    return { wind: true, wave: true, current: true, cyclones: true };
  });
  const toggleClimoFilter = useCallback((id, on) => {
    setClimoFilters((prev) => {
      const next = { ...prev, [id]: !!on };
      try { localStorage.setItem("bi.climoFilters.v2", JSON.stringify(next)); } catch (_) { /* ignore */ }
      return next;
    });
  }, []);
  const [climoWaveStat, setClimoWaveStat] = useState("mean");
  const [climoMeta, setClimoMeta] = useState(null);
  const [climoPoint, setClimoPoint] = useState(null);
  // Phase 8 — Anchorages (mouillages) layer
  const [anchorages, setAnchorages] = useState({ type: "FeatureCollection", features: [] });
  const [showAnchorages, setShowAnchoragesRaw] = useState(() => {
    try { return localStorage.getItem("bi.showAnchorages") !== "0"; } catch (_) { return true; }
  });
  const setShowAnchorages = useCallback((v) => {
    setShowAnchoragesRaw(v);
    try { localStorage.setItem("bi.showAnchorages", v ? "1" : "0"); } catch (_) { /* ignore */ }
  }, []);
  // Refactor 2026-06 — Formalities mode = world [EEZ -> Ports of Entry]
  const [poeZones, setPoeZones] = useState({ count: 0, summary: null, items: [] });
  const [poeZonesLoading, setPoeZonesLoading] = useState(true);
  const [poePorts, setPoePorts] = useState({ type: "FeatureCollection", features: [] });
  const [selectedZone, setSelectedZone] = useState(null);   // mrgid
  const [selectedZoneName, setSelectedZoneName] = useState(null);
  const [flyToZone, setFlyToZone] = useState(null);         // {mrgid, bbox, ts}
  const [zoneFiche, setZoneFiche] = useState(null);
  // Current selection, readable from the stable handleSelectZone callback.
  const selectedZoneRef = useRef(null);
  const zoneFicheRef = useRef(null);
  selectedZoneRef.current = selectedZone;
  zoneFicheRef.current = zoneFiche;
  const [verifyState, setVerifyState] = useState({ mrgid: null, running: false, error: null });
  const [ficheLoading, setFicheLoading] = useState(false);
  const [mapEpoch, setMapEpoch] = useState(0);
  const [flyToPoe, setFlyToPoe] = useState(null);
  const [ampSites, setAmpSites] = useState({ type: "FeatureCollection", features: [] });
  const [flyToAmp, setFlyToAmp] = useState(null);
  // Run selector (">" button on the Map tab) — { [mode]: {id,label} | null }.
  // When a run is selected, the map shows that run's data instead of live.
  const [mapRuns, setMapRuns] = useState({});
  const mapRunsRef = useRef(mapRuns);
  mapRunsRef.current = mapRuns;
  const userPickedRunRef = useRef({});
  const lastFitKeyRef = useRef("");
  const [fitRunBounds, setFitRunBounds] = useState(null);
  // Phase 7bis stabilisation — memoise `t` so its reference stays stable
  // across selection setStates. Otherwise every `handleSelectEscale` call
  // creates a fresh `t` → MapView props change → the formalities marker
  // rebuild useEffect re-fires and the DOM briefly drops to 0 markers.
  const t = useMemo(() => makeT(lang), [lang]);
  useEffect(() => {
    setNotForNavOk(readNotForNavAccepted(
      undefined, t("notForNavTitle"), t("notForNavBody"),
    ));
  }, [t]);
  const nauticalAllowed = notForNavOk;
  const notForNavOpen = siteEntryNeedsAccept(notForNavOk);
  const lastTotalRef = useRef(-1);
  const viewRef = useRef(view);
  viewRef.current = view;

  // Resolve admin status from /admin/check on boot: open by default locally
  // (ADMIN_KEY unset → admin_required: false → Console/Review reachable),
  // protected in prod (ADMIN_KEY set → key required).
  useEffect(() => {
    let alive = true;
    const resolveAdmin = async () => {
      try {
        const { data } = await api.get("/admin/check");
        if (!alive) return;
        setIsAdmin(!data.admin_required || hasAdminKey());
        setAdminChecked(true);
      } catch (_) {
        if (!alive) return;
        setIsAdmin(false);
        setAdminChecked(true);
      }
    };
    resolveAdmin();
    return () => { alive = false; };
  }, []);

  // Without admin rights, Console (audit) and Review views are unreachable.
  useEffect(() => {
    if (!isAdmin && (view === "audit" || view === "review")) setView("map");
  }, [isAdmin, view, adminChecked]);

  // Persist mode + reflect on <html> for CSS var switching
  const setMode = useCallback((m) => {
    lastFitKeyRef.current = "";
    setModeRaw(m);
    try { localStorage.setItem("bi.mode", m); } catch (_) { /* ignore */ }
    if ((m === "science" || m === "climatology") && viewRef.current === "review") setView("map");
  }, []);

  useEffect(() => {
    // Set data-mode on <html> so [data-mode="..."] CSS vars kick in globally
    document.documentElement.setAttribute("data-mode", mode);
  }, [mode]);

  const fetchStatus = useCallback(async () => {
    try {
      const { data } = await api.get("/swarm/status");
      setStatus(data);
    } catch (e) { /* transient */ }
  }, []);

  const fetchProjects = useCallback(async (force = false) => {
    try {
      if (showReviewRef.current) {
        const f = await api.get("/funders", { params: { visible: true } });
        setFunders(f.data);
        const p = await api.get("/projects", { params: { visible: true } });
        setProjects(p.data);
        lastTotalRef.current = -1;
        return;
      }
      const run = mapRunsRef.current.projects;
      if (run?.id) {
        const p = await api.get(`/projects/runs/${run.id}/geojson`);
        setProjects(p.data);
        lastTotalRef.current = -1;   // back to live => full refetch
        const n = p.data?.features?.length || 0;
        const key = `projects:${run.id}:${n}`;
        if (n && lastFitKeyRef.current !== key) {
          lastFitKeyRef.current = key;
          const points = latLngsFromFc(p.data);
          if (points.length) setFitRunBounds({ ts: Date.now(), points });
        }
        return;
      }
      const f = await api.get("/funders");
      setFunders(f.data);
      if (force || f.data.total !== lastTotalRef.current) {
        const p = await api.get("/projects");
        setProjects(p.data);
        lastTotalRef.current = f.data.total;
      }
    } catch (e) { /* transient */ }
  }, []);

  const fetchSettings = useCallback(async () => {
    try {
      const { data } = await api.get("/settings");
      setSettings(data);
    } catch (e) { /* transient */ }
  }, []);

  const fetchCategories = useCallback(async () => {
    try {
      const { data } = await api.get("/categories");
      setCategories(data.groups);
    } catch (e) { /* transient */ }
  }, []);

  const projectsRef = useRef(projects);
  projectsRef.current = projects;

  const marinasRef = useRef(marinas);
  marinasRef.current = marinas;

  const fetchMarinas = useCallback(async (force = false) => {
    try {
      const run = mapRunsRef.current.marinas;
      if (!force && !run?.id
          && (marinasRef.current?.features?.length || 0) > 0) {
        return;
      }
      const { data } = showReviewRef.current
        ? await api.get("/marinas", { timeout: 300000, params: { visible: true } })
        : run?.id
          ? await api.get(`/marinas/runs/${run.id}/geojson`, { timeout: 300000 })
          : await api.get("/marinas", { timeout: 300000 });
      setMarinas(data);
      if (run?.id) {
        const n = data?.features?.length || 0;
        const key = `marinas:${run.id}:${n}`;
        if (n && lastFitKeyRef.current !== key) {
          lastFitKeyRef.current = key;
          const points = latLngsFromFc(data);
          if (points.length) setFitRunBounds({ ts: Date.now(), points });
        }
      }
    } catch (e) { /* transient */ }
  }, []);

  const capitaineriesRef = useRef(capitaineries);
  capitaineriesRef.current = capitaineries;

  const fetchCapitaineries = useCallback(async (force = false) => {
    try {
      const run = mapRunsRef.current.capitaineries;
      if (!force && !run?.id && (capitaineriesRef.current?.features?.length || 0) > 0) return;
      const { data } = showReviewRef.current
        ? await api.get("/capitaineries", { params: { visible: true } })
        : run?.id
          ? await api.get(`/capitaineries/runs/${run.id}/geojson`)
          : await api.get("/capitaineries");
      setCapitaineries(data);
      if (run?.id) {
        const n = data?.features?.length || 0;
        const key = `capitaineries:${run.id}:${n}`;
        if (n && lastFitKeyRef.current !== key) {
          lastFitKeyRef.current = key;
          const points = latLngsFromFc(data);
          if (points.length) setFitRunBounds({ ts: Date.now(), points });
        }
      }
    } catch (e) { /* transient */ }
  }, []);

  // Phase 8 — anchorages fetcher
  const fetchAnchorages = useCallback(async () => {
    try {
      const { data } = await api.get("/anchorages");
      setAnchorages(data);
    } catch (e) { /* transient */ }
  }, []);

  // Science mode — GeoJSON comes from the live science_items collection
  // (non-destructive harvest); no per-run variant and no review filter.
  const fetchScience = useCallback(async () => {
    try {
      const { data } = await api.get("/science");
      setScience(data);
    } catch (e) { /* transient */ }
  }, []);

  const fetchClimoMeta = useCallback(async (month) => {
    try {
      const { data } = await api.get("/climatology/meta", { params: { month } });
      setClimoMeta(data);
      const st = data?.snapshot?.wave_stat;
      if (st === "mean") setClimoWaveStat("mean");
      else if (st === "p50_p90") {
        setClimoWaveStat((prev) => (prev === "mean" ? "p90" : prev));
      }
    } catch (e) { /* transient */ }
  }, []);

  const fetchPoeZones = useCallback(async () => {
    try {
      const { data } = await api.get("/poe/zones", {
        params: showReviewRef.current ? { visible: true } : {},
      });
      setPoeZones(data);
    } catch (e) { /* transient */ }
    finally { setPoeZonesLoading(false); }
  }, []);

  const poePortsRef = useRef(poePorts);
  poePortsRef.current = poePorts;

  const fetchPoePorts = useCallback(async (force = false) => {
    try {
      const run = mapRunsRef.current.formalities;
      if (!force && !run?.id && (poePortsRef.current?.features?.length || 0) > 0) return;
      const { data } = showReviewRef.current
        ? await api.get("/poe/ports", { params: { visible: true } })
        : run?.id
          ? await api.get(`/poe/runs/${run.id}/ports`)
          : await api.get("/poe/ports");
      setPoePorts(data);
    } catch (e) { /* transient */ }
  }, []);

  // Lazy per-mode datasets (perf 2026-10): a dataset is "wanted" once
  // loaded, or when the current mode displays it.
  const modeRef = useRef(mode);
  modeRef.current = mode;
  const loadedRef = useRef(new Set());
  const isWanted = useCallback((key) => {
    if (loadedRef.current.has(key)) return true;
    return (MODE_DATASETS[modeRef.current] || []).includes(key);
  }, []);

  const refreshMapData = useCallback(() => {
    fetchProjects(true);
    // Only datasets already loaded (or shown by the current mode) — see
    // the lazy per-mode loading below.
    if (isWanted("marinas")) fetchMarinas(true);
    if (isWanted("capitaineries")) fetchCapitaineries(true);
    if (isWanted("poeZones")) fetchPoeZones();
    if (isWanted("poePorts")) fetchPoePorts(true);
    setMapEpoch((n) => n + 1);
  }, [fetchProjects, fetchMarinas, fetchCapitaineries, fetchPoeZones, fetchPoePorts, isWanted]);

  useEffect(() => {
    // Phase 3.1 — async enrichment via 202 + poll status.
    // Polls every 2.5s until state != "running" (max ~180s).
    const pollUntilDone = async (endpoint, onDone, onErr, maxAttempts = 72) => {
      for (let i = 0; i < maxAttempts; i++) {
        // 2.5s between polls
        await new Promise((res) => setTimeout(res, 2500));
        try {
          const st = await api.get(endpoint);
          const s = st.data?.state;
          if (s === "done") { onDone(st.data); return; }
          if (s === "error") { onErr(st.data?.error || "enrichment failed"); return; }
        } catch (e) { /* transient */ }
      }
      onErr("timeout after ~3min");
    };

    window.__biEnrichMarina = async (marinaId) => {
      const btn = document.querySelector(`[data-testid="popup-enrich-btn"]`);
      const setBtn = (label, color) => {
        if (!btn) return;
        btn.textContent = label;
        if (color) btn.style.color = color;
      };
      try {
        if (btn) btn.disabled = true;
        setBtn("◆ " + (lang === "fr" ? "Enrichissement…" : "Enriching…"));
        // 202 kick-off (<5s)
        const kick = await api.post(`/marinas/${marinaId}/enrich`);
        if (kick.status !== 202 && kick.status !== 200) {
          setBtn("◆ " + (lang === "fr" ? "Échec" : "Failed"), "#fbbf24");
          return;
        }
        // Poll
        await pollUntilDone(
          `/marinas/${marinaId}/enrich/status`,
          async (data) => {
            await fetchMarinas(true);
            const m = data.result || {};
            setFlyToMarina({ id: marinaId, lat: m.lat, lon: m.lon, ts: Date.now() });
          },
          (err) => {
            setBtn("◆ " + (lang === "fr" ? "Échec" : "Failed"), "#fbbf24");
            if (btn) btn.title = String(err).slice(0, 200);
          },
        );
      } catch (e) {
        // 409 = already running — attach the poller anyway
        if (e?.response?.status === 409) {
          await pollUntilDone(
            `/marinas/${marinaId}/enrich/status`,
            async (data) => {
              await fetchMarinas(true);
              const m = data.result || {};
              setFlyToMarina({ id: marinaId, lat: m.lat, lon: m.lon, ts: Date.now() });
            },
            (err) => setBtn("◆ " + (lang === "fr" ? "Échec" : "Failed"), "#fbbf24"),
          );
        } else {
          setBtn("◆ " + (lang === "fr" ? "Échec" : "Failed"), "#fbbf24");
          console.warn("marina enrich failed", e);
        }
      }
    };

    window.__biEnrichProject = async (projectId) => {
      const btn = document.querySelector(`[data-testid="popup-project-enrich-btn"]`);
      const setBtn = (label, color) => {
        if (!btn) return;
        btn.textContent = label;
        if (color) btn.style.color = color;
      };
      try {
        if (btn) btn.disabled = true;
        setBtn("↻ " + (lang === "fr" ? "Rafraîchissement…" : "Refreshing…"));
        const kick = await api.post(`/projects/${projectId}/enrich`);
        if (kick.status !== 202 && kick.status !== 200) {
          setBtn("↻ " + (lang === "fr" ? "Échec" : "Failed"), "#fbbf24");
          return;
        }
        await pollUntilDone(
          `/projects/${projectId}/enrich/status`,
          async () => {
            await fetchProjects(true);
            setBtn("✓ " + (lang === "fr" ? "Rafraîchi" : "Refreshed"), "#39ff14");
          },
          (err) => {
            setBtn("↻ " + (lang === "fr" ? "Échec" : "Failed"), "#fbbf24");
            if (btn) btn.title = String(err).slice(0, 200);
          },
        );
      } catch (e) {
        if (e?.response?.status === 409) {
          await pollUntilDone(
            `/projects/${projectId}/enrich/status`,
            async () => {
              await fetchProjects(true);
              setBtn("✓ " + (lang === "fr" ? "Rafraîchi" : "Refreshed"), "#39ff14");
            },
            (err) => setBtn("↻ " + (lang === "fr" ? "Échec" : "Failed"), "#fbbf24"),
          );
        } else {
          setBtn("↻ " + (lang === "fr" ? "Échec" : "Failed"), "#fbbf24");
          console.warn("project enrich failed", e);
        }
      }
    };

    return () => {
      delete window.__biEnrichMarina;
      delete window.__biEnrichProject;
    };
  }, [fetchMarinas, fetchProjects, lang]);

  // Perf 2026-10 (Lighthouse mobile) — heavy per-mode datasets (marinas
  // ~15 MB, science ~8 MB, PoE ports ~0.8 MB, capitaineries, anchorages)
  // are fetched only when their mode is opened (or once loaded, refreshed by
  // the polls). Before, every visit parsed ~27 MB of GeoJSON and built every
  // Leaflet cluster at boot even though only the active mode is displayed.
  const DATASET_FETCHERS = useMemo(() => ({
    marinas: fetchMarinas,
    anchorages: fetchAnchorages,
    capitaineries: fetchCapitaineries,
    poeZones: fetchPoeZones,
    poePorts: fetchPoePorts,
    science: fetchScience,
  }), [fetchMarinas, fetchAnchorages, fetchCapitaineries, fetchPoeZones, fetchPoePorts, fetchScience]);

  useEffect(() => {
    for (const key of MODE_DATASETS[mode] || []) {
      if (loadedRef.current.has(key)) continue;
      loadedRef.current.add(key);
      DATASET_FETCHERS[key]();
    }
  }, [mode, DATASET_FETCHERS]);

  // Admin console shows the anchorages count.
  useEffect(() => {
    if (view !== "audit" || loadedRef.current.has("anchorages")) return;
    loadedRef.current.add("anchorages");
    fetchAnchorages();
  }, [view, fetchAnchorages]);

  // Perf 2026-10: in projects mode the map shows the default isolated run
  // (picked by the run sync below), so the live /api/projects dump (~3.5 MB)
  // fetched at boot was parsed then immediately replaced. At boot we only
  // load the funders; the live dump is fetched only if no run gets picked.
  const fetchFundersOnly = useCallback(async () => {
    try {
      const f = await api.get("/funders");
      setFunders(f.data);
    } catch (e) { /* transient */ }
  }, []);

  useEffect(() => {
    fetchStatus();
    let projectsFallback = null;
    if (modeRef.current === "projects" && !showReviewRef.current) {
      fetchFundersOnly();
      projectsFallback = setTimeout(() => {
        if (mapRunsRef.current.projects?.id) return;
        if ((projectsRef.current?.features?.length || 0) > 0) return;
        fetchProjects(true);
      }, 6000);
    } else {
      fetchProjects();
    }
    fetchSettings();
    fetchClimoMeta(new Date().getMonth() + 1);
    // Tiny payload, drives the projects legend: no longer delayed now that
    // the heavy per-mode dumps are not fetched at boot.
    fetchCategories();
    const unlessReview = (fn) => () => {
      if (viewRef.current === "review") return;
      fn();
    };
    const ifWanted = (key, fn) => () => {
      if (!isWanted(key)) return;
      fn();
    };
    const fetchMarinasIfIdle = async () => {
      if (viewRef.current === "review") return;
      if (!isWanted("marinas")) return;
      if (mapRunsRef.current.marinas?.id) {
        await fetchMarinas(true);
        return;
      }
      if ((marinasRef.current?.features?.length || 0) > 1000) return;
      try {
        const { data } = await api.get("/marinas/build/status", { timeout: 5000 });
        if (data?.running) return;
      } catch (_) {
        return;
      }
      await fetchMarinas();
    };
    // Staggered polls (keep the UI fluid): full GeoJSON payloads are heavy;
    // panels force a targeted refresh as soon as a build finishes.
    const s = setInterval(fetchStatus, 4000);
    const p = setInterval(unlessReview(() => fetchProjects()), 30000);
    const c = setInterval(fetchCategories, 60000);
    const m = setInterval(fetchMarinasIfIdle, 180000);
    const cap = setInterval(unlessReview(ifWanted("capitaineries", () => fetchCapitaineries())), 60000);
    const a = setInterval(unlessReview(ifWanted("anchorages", fetchAnchorages)), 120000);
    const sci = setInterval(unlessReview(ifWanted("science", fetchScience)), 180000);
    const z = setInterval(unlessReview(ifWanted("poeZones", fetchPoeZones)), 60000);
    const pp = setInterval(unlessReview(ifWanted("poePorts", () => fetchPoePorts())), 60000);
    return () => {
      if (projectsFallback) clearTimeout(projectsFallback);
      clearInterval(s); clearInterval(p); clearInterval(c); clearInterval(m);
      clearInterval(cap); clearInterval(a); clearInterval(sci); clearInterval(z); clearInterval(pp);
    };
  }, [fetchStatus, fetchProjects, fetchFundersOnly, fetchSettings, fetchCategories, fetchMarinas, fetchCapitaineries, fetchAnchorages, fetchScience, fetchClimoMeta, fetchPoeZones, fetchPoePorts, isWanted]);

  // Select a run to display (null = live map) for the current mode.
  const handleSelectMapRun = useCallback((run) => {
    userPickedRunRef.current[mode] = true;
    lastFitKeyRef.current = "";
    setMapRuns((prev) => ({ ...prev, [mode]: run || null }));
  }, [mode]);

  // Default Map layer = the mode's isolated run (contract §8). Formalities unchanged.
  useEffect(() => {
    if (mode === "formalities" || mode === "science" || mode === "climatology") return undefined;
    const ep = RUNS_LIST_EP[mode];
    if (!ep) return undefined;
    let alive = true;
    const sync = async () => {
      try {
        let runningId = null;
        if (mode === "marinas") {
          const { data } = await api.get("/marinas/build/status", { timeout: 5000 });
          if (data?.run_id) runningId = data.run_id;
        } else if (mode === "capitaineries") {
          const { data } = await api.get("/capitaineries/build/status", { timeout: 5000 });
          if (data?.run_id) runningId = data.run_id;
        } else if (mode === "amp") {
          const { data } = await api.get("/amp/discover-visit-urls/status", { timeout: 5000 });
          if (data?.run_id) runningId = data.run_id;
        } else if (mode === "projects") {
          const { data } = await api.get("/swarm/status", { timeout: 5000 });
          if (data?.run_id) runningId = data.run_id;
        }
        const { data } = await api.get(ep);
        const items = (data?.items || []).filter((r) => !r.wrote_live);
        const worldItems = items.filter((r) => String(r.label || "").startsWith("test-world"));
        const testItems = items.filter((r) => String(r.label || "").startsWith("test-map-30"));
        const pool = worldItems.length ? worldItems : (testItems.length ? testItems : items);
        const running = runningId && pool.find((r) => r.id === runningId);
        const pick = running || pool.find((r) => r.state === "running") || pool[0];
        if (!alive) return;
        setMapRuns((prev) => {
          if (runningId && prev[mode]?.id !== runningId) {
            return { ...prev, [mode]: { id: runningId, label: running?.label || runningId } };
          }
          if (mode in prev) return prev;
          if (!pick) return prev;
          return { ...prev, [mode]: { id: pick.id, label: pick.label || pick.id } };
        });
      } catch (_) { /* transient */ }
    };
    sync();
    const tmr = setInterval(sync, 4000);
    return () => { alive = false; clearInterval(tmr); };
  }, [mode]);

  useEffect(() => {
    const run = mapRuns.amp;
    if (!run?.id) return;
    const n = ampSites?.features?.length || 0;
    const key = `amp:${run.id}:${n}`;
    if (n && lastFitKeyRef.current !== key) {
      lastFitKeyRef.current = key;
      const points = latLngsFromFc(ampSites);
      if (points.length) setFitRunBounds({ ts: Date.now(), points });
    }
  }, [ampSites, mapRuns]);

  // Selected run changed => immediately re-fetch the affected dataset.
  const prevMapRunsRef = useRef({});
  useEffect(() => {
    const prev = prevMapRunsRef.current;
    const next = mapRuns;
    prevMapRunsRef.current = next;
    const changed = Object.keys({ ...prev, ...next }).filter(
      (k) => (prev[k]?.id || null) !== (next[k]?.id || null),
    );
    if (!changed.length) return;
    if (changed.includes("projects")) fetchProjects(true);
    if (changed.includes("marinas")) fetchMarinas(true);
    if (changed.includes("capitaineries")) fetchCapitaineries(true);
    if (changed.includes("formalities")) fetchPoePorts(true);
    if (changed.includes("amp")) setMapEpoch((n) => n + 1);
  }, [mapRuns, fetchProjects, fetchMarinas, fetchCapitaineries, fetchPoePorts]);

  // Handler passed to MarinasPanel — sets a one-shot fly target consumed by MapView
  const handleFlyToMarina = useCallback((id, lat, lon) => {
    setFlyToMarina({ id, lat, lon, ts: Date.now() });
  }, []);

  const handleFlyToCapitainerie = useCallback((id, lat, lon) => {
    setFlyToCapitainerie({ id, lat, lon, ts: Date.now() });
  }, []);

  const handleFlyToScience = useCallback((id, lat, lon) => {
    setFlyToScience({ id, lat, lon, ts: Date.now() });
  }, []);

  useEffect(() => {
    if (mode !== "climatology") return undefined;
    fetchClimoMeta(climoMonth);
    return undefined;
  }, [mode, climoMonth, fetchClimoMeta]);

// Refactor 2026-06 — Handler wired to the sidebar rows and the EEZ polygons:
// selects the zone; when a bbox is supplied (sidebar click), also flies to it.
// Simple read-only fetch of the zone fiche via GET /poe/zones/{mrgid};
// no POST /api/poe/verify is triggered on click.
// Selecting the zone already open (its polygon, its row) keeps the sheet as it is,
// verify result included; only a different zone resets and refetches it.
const handleSelectZone = useCallback(async (mrgid, zoneName, bbox, anchor) => {
  if (mrgid == null) {
    // "All zones": close the sheet, back to the list.
    setSelectedZone(null);
    setSelectedZoneName(null);
    setZoneFiche(null);
    setFicheLoading(false);
    return;
  }
  const sameZone = Number(selectedZoneRef.current) === Number(mrgid)
    && zoneFicheRef.current && Number(zoneFicheRef.current.mrgid) === Number(mrgid);
  setSelectedZone(mrgid);
  setSelectedZoneName(zoneName ?? null);
  if (!sameZone) {
    setZoneFiche(null);
    setFicheLoading(true);
    try {
      const { data } = await api.get(`/poe/zones/${mrgid}`);
      setZoneFiche(data);
    } catch (_) {
      setZoneFiche(null);
    } finally {
      setFicheLoading(false);
    }
  }
  if (bbox && Array.isArray(bbox) && bbox.length === 4) {
    setFlyToZone({ mrgid, bbox, anchor: anchor || null, ts: Date.now() });
  }
}, []);

  // Explicit "Verify" in the fiche: POST /poe/verify (Nemotron + Zetaris, ~50 s), merged
  // into the fiche of the zone it started for; a result arriving after the user moved
  // to another zone is dropped.
  const handleVerifyZone = useCallback(async () => {
    const mrgid = selectedZone;
    const zoneName = zoneFiche?.name || zoneFiche?.geoname || selectedZoneName || "";
    if (!mrgid || !zoneName) return;
    setVerifyState({ mrgid, running: true, error: null });
    try {
      const data = await verifyZonePoe(zoneName, mrgid);
      setZoneFiche((f) => (f && Number(f.mrgid) === Number(mrgid) ? mergeVerifyIntoFiche(f, data) : f));
      setVerifyState((v) => (v.mrgid === mrgid ? { mrgid, running: false, error: data?.error || null } : v));
    } catch (e) {
      const detail = e?.response?.data?.detail || e?.message || String(e);
      setVerifyState((v) => (v.mrgid === mrgid ? { mrgid, running: false, error: String(detail) } : v));
    }
  }, [selectedZone, selectedZoneName, zoneFiche]);

  const handleFlyToPoe = useCallback((port) => {
    if (!port || port.lat == null || port.lon == null) return;
    setFlyToPoe({ ...port, ts: Date.now() });
  }, []);

  const handleFlyToAmp = useCallback((id, lat, lon) => {
    if (lat == null || lon == null) return;
    setFlyToAmp({ id, lat, lon, ts: Date.now() });
  }, []);

  useEffect(() => {
    if (!selectedZone) {
      setZoneFiche(null);
      setFicheLoading(false);
      return;
    }
    // The fiche is loaded by handleSelectZone (read-only GET /poe/zones/{mrgid});
    // POST /poe/verify only runs from the fiche's Verify button (handleVerifyZone).
    return () => { /* noop */ };
  }, [selectedZone, mapEpoch]);

  return (
    <div className="h-screen w-screen flex flex-col overflow-hidden bg-abyss" data-mode={mode}>
      <Header
        lang={lang} setLang={setLang} view={view} setView={setView}
        showSettings={showSettings} setShowSettings={setShowSettings}
        status={status} t={t} basemap={basemap} setBasemap={setBasemap}
        mode={mode} setMode={setMode}
        mapRun={mapRuns[mode] || null}
        onSelectMapRun={handleSelectMapRun}
        isAdmin={isAdmin}
        showReview={showReview}
        onToggleShowReview={(on) => {
          setShowReview(on);
          refreshMapData();
        }}
      />
      <div className="flex flex-1 min-h-0">
        {view !== "review" && mode === "projects" && (
          <SwarmPanel
            t={t} projects={projects} funders={funders}
            funderFilter={funderFilter} setFunderFilter={setFunderFilter}
            searchQuery={searchQuery} setSearchQuery={setSearchQuery}
            categories={categories} categoryFilter={categoryFilter} setCategoryFilter={setCategoryFilter}
            onFlyTo={(id, lat, lon) => setFlyToProject({ id, lat, lon, ts: Date.now() })}
            onReport={() => setShowReport(true)}
          />
        )}
        {view !== "review" && mode === "marinas" && (
          <MarinasPanel
            t={t}
            marinas={marinas}
            onFlyTo={handleFlyToMarina}
            onRefresh={fetchMarinas}
            onRefreshAnchorages={fetchAnchorages}
          />
        )}
        {view !== "review" && mode === "capitaineries" && (
          <CapitaineriesPanel
            t={t}
            capitaineries={capitaineries}
            onFlyTo={handleFlyToCapitainerie}
            onRefresh={fetchCapitaineries}
          />
        )}
        {view !== "review" && mode === "formalities" && (
          <FormalitiesPanel
            t={t}
            lang={lang}
            zones={poeZones}
            zonesLoading={poeZonesLoading}
            selectedZone={selectedZone}
            onSelectZone={handleSelectZone}
            fiche={zoneFiche}
            ficheLoading={ficheLoading}
            onFlyToPort={handleFlyToPoe}
            onVerify={handleVerifyZone}
            verifyState={verifyState.mrgid === selectedZone ? verifyState : null}
          />
        )}
        {view !== "review" && mode === "amp" && (
          <AmpPanel
            t={t}
            sites={ampSites}
            lfpFilter={ampLfpFilter}
            onLfpFilter={setAmpLfpFilter}
            onFlyTo={handleFlyToAmp}
          />
        )}
        {view !== "review" && mode === "science" && (
          <SciencePanel
            t={t}
            science={science}
            onFlyTo={handleFlyToScience}
            onRefresh={fetchScience}
            sourceFilter={scienceSourceFilter}
            onSourceFilter={setScienceSourceFilter}
          />
        )}
        {view !== "review" && mode === "climatology" && (
          <ClimatologyPanel
            t={t}
            lang={lang}
            month={climoMonth}
            onMonth={(m) => { setClimoMonth(m); setClimoPoint(null); }}
            filters={climoFilters}
            onToggleFilter={toggleClimoFilter}
            waveStat={climoWaveStat}
            onWaveStat={setClimoWaveStat}
            meta={climoMeta}
            point={climoPoint}
          />
        )}
        <main className="flex-1 relative min-w-0">
          <div
            className={view === "map" ? "absolute inset-0" : "absolute inset-0 invisible pointer-events-none"}
            aria-hidden={view !== "map"}
          >
            <MapView
              mode={mode}
              projects={projects}
              marinas={marinas}
              capitaineries={capitaineries}
              flyToCapitainerie={flyToCapitainerie}
              science={science}
              flyToScience={flyToScience}
              scienceWms={scienceWms}
              overlayOn={overlayOn}
              nauticalAllowed={nauticalAllowed}
              safetyM={safetyM}
              noaaAidsOn={noaaAidsOn}
              showReview={showReview}
              scienceSourceFilter={scienceSourceFilter}
              climoMonth={climoMonth}
              climoFilters={climoFilters}
              climoWaveStat={climoWaveStat}
              onClimoPoint={setClimoPoint}
              ampLfpFilter={ampLfpFilter}
              anchorages={anchorages}
              showAnchorages={showAnchorages}
              poeZones={poeZones.items}
              poePorts={poePorts}
              selectedZone={selectedZone}
              lang={lang}
              onSelectZone={handleSelectZone}
              flyToMarina={flyToMarina}
              flyToZone={flyToZone}
              flyToPoe={flyToPoe}
              flyToAmp={flyToAmp}
              flyToProject={flyToProject}
              fitRunBounds={fitRunBounds}
              ampRunId={showReview ? null : (mapRuns.amp?.id || null)}
              onAmpSites={setAmpSites}
              zoneFiche={zoneFiche}
              funderFilter={funderFilter} searchQuery={searchQuery} t={t}
              basemap={basemap} categories={categories} categoryFilter={categoryFilter}
              minZoom={settings?.min_zoom || 2}
              mapVisible={view === "map"}
              mapRun={mapRuns[mode] || null} />
          </div>
          {view === "audit" ? (
            <AuditView t={t} lang={lang} mode={mode} status={status} refresh={() => { fetchStatus(); fetchProjects(); }}
              settings={settings} onSettingsSaved={fetchSettings}
              onPoeRefresh={() => { fetchPoeZones(); fetchPoePorts(true); }}
              showAnchorages={showAnchorages} setShowAnchorages={setShowAnchorages}
              anchoragesCount={anchorages?.features?.length || 0} />
          ) : view === "review" ? (
            mode === "science" || mode === "climatology" ? (
              <div className="h-full flex items-center justify-center p-8" data-testid={mode === "science" ? "review-science-placeholder" : "review-climatology-placeholder"}>
                <p className="max-w-md text-center text-sm text-slate-400 leading-relaxed">
                  {t(mode === "science" ? "reviewScienceUnavailable" : "reviewClimatologyUnavailable")}
                </p>
              </div>
            ) : (
              <ReviewView t={t} lang={lang} mode={mode} onMapDirty={refreshMapData} />
            )
          ) : null}
        </main>
          {showSettings && (
          <SettingsPanel t={t} lang={lang} mode={mode} settings={settings}
            isAdmin={isAdmin}
            overlayOn={overlayOn}
            onToggleOverlay={setOverlayOn}
            scienceWms={scienceWms}
            onToggleWms={toggleScienceWms}
            safetyM={safetyM}
            onSafetyM={setSafetyM}
            noaaAidsOn={noaaAidsOn}
            onToggleNoaaAids={setNoaaAidsOn}
            showNoaa={mode === "capitaineries"}
            onSaved={fetchSettings}
            // 2026-08-24 bug-fix — import router-callback receives the mode
            // that was actually imported so we only refresh the affected
            // dataset (never both, to avoid unnecessary re-fetches).
            onImported={(importedMode) => {
              if (importedMode === "marinas") fetchMarinas(true);
              else if (importedMode === "capitaineries") fetchCapitaineries(true);
              else if (importedMode === "science") fetchScience();
              else fetchProjects(true);
            }}
            onProjectsCleared={() => fetchProjects(true)} onClose={() => setShowSettings(false)} />
        )}
      </div>
      {showReport && (
        <ReportModal t={t} onClose={() => setShowReport(false)} onSubmitted={() => { setShowReport(false); }} />
      )}
      <NotForNavModal
        t={t}
        open={notForNavOpen}
        onAccept={() => {
          writeNotForNavAccepted(
            undefined, t("notForNavTitle"), t("notForNavBody"),
          );
          setNotForNavOk(true);
        }}
      />
    </div>
  );
}
