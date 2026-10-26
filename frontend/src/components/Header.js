import { Anchor, ClipboardCheck, Compass, Eye, FlaskConical, Map as MapIcon, Moon, Radar, Radio, ScrollText, Settings, Shield, Ship, Sun, UserPlus, Waves, Wind } from "lucide-react";
import RunSelector from "./RunSelector";
import { HELLOASSO_MEMBERSHIP_URL } from "../config/helloasso";
import { nextBasemap } from "./map/basemaps";

// Icon and label of the NEXT basemap (the button announces its destination).
const BASEMAP_NEXT_UI = {
  dark: { Icon: Moon, titleKey: "darkMap" },
  light: { Icon: Sun, titleKey: "lightMap" },
  sea: { Icon: Ship, titleKey: "seaMap" },
};

// Seven data modes: projects / marinas / capitaineries / formalities / amp / science / climatology.
const MODES = [
  { id: "projects", Icon: Compass, labelKey: "modeProjects" },
  { id: "marinas", Icon: Anchor, labelKey: "modeMarinas" },
  { id: "capitaineries", Icon: Radio, labelKey: "modeCapitaineries" },
  { id: "formalities", Icon: ScrollText, labelKey: "modeFormalities" },
  { id: "amp", Icon: Shield, labelKey: "modeAmp" },
  { id: "science", Icon: FlaskConical, labelKey: "modeScience" },
  { id: "climatology", Icon: Wind, labelKey: "modeClimatology" },
];

const ICON = { size: 14, strokeWidth: 1.75 };

export default function Header({
  lang, setLang, view, setView, showSettings, setShowSettings,
  status, t, basemap, setBasemap,
  mode, setMode,
  mapRun, onSelectMapRun,
  isAdmin = false,
  showReview = false,
  onToggleShowReview,
}) {
  const next = nextBasemap(basemap);
  const { Icon: BasemapIcon, titleKey } = BASEMAP_NEXT_UI[next] || BASEMAP_NEXT_UI.dark;
  return (
    <header className="h-12 shrink-0 flex items-center justify-between gap-4 px-4 border-b border-line bg-surface z-[1200] font-ui text-[13px] whitespace-nowrap">
      <div className="flex items-center gap-3 min-w-0">
        <div className="w-7 h-7 flex items-center justify-center border border-line rounded-md text-m-fg2 shrink-0" aria-hidden="true">
          <Waves size={15} strokeWidth={1.75} />
        </div>
        <h1 className="m-0 leading-none" title={t("subtitle")}>
          <span className="block text-[13px] leading-4 font-semibold text-m-fg">Blue Intelligence</span>
          <span className="block text-[11px] leading-4 text-m-fg3">by Berry-Mappemonde</span>
        </h1>
        {status?.running && (
          <span className="ml-1 inline-flex items-center gap-2 h-6 px-2 border border-line rounded-md text-[12px] text-m-fg2" data-testid="swarm-running">
            <span className="w-1.5 h-1.5 rounded-full bg-bio animate-pulse" aria-hidden="true" />
            {t("runningStatus")}
          </span>
        )}
      </div>
      <nav className="flex items-center gap-1.5" aria-label={t("modeSwitchTitle")}>
        {/* Seven-mode switch — projects / marinas / capitaineries / formalities / amp / science / climatology */}
        <div className="nav-group" title={t("modeSwitchTitle")} data-testid="mode-switch">
          {MODES.map(({ id, Icon, labelKey }) => (
            <button
              key={id}
              type="button"
              data-testid={`mode-toggle-${id}`}
              onClick={() => setMode(id)}
              className="nav-tab"
              aria-current={mode === id ? "true" : undefined}
              title={id === "climatology" ? t("modeClimatologyFull") : t(labelKey)}
            >
              {/* Below 1400 px only the active mode keeps its label; every tab keeps its title. */}
              <Icon {...ICON} /> <span className={mode === id ? "inline" : "hidden min-[1400px]:inline"}>{t(labelKey)}</span>
            </button>
          ))}
        </div>
        <div className="nav-group">
          <button
            type="button"
            data-testid="view-toggle-map"
            onClick={() => setView("map")}
            className="nav-tab"
            aria-current={view === "map" ? "true" : undefined}
          >
            <MapIcon {...ICON} /> {t("map")}
          </button>
          {/* "Runs ›" — selector for the run shown on the map (per mode).
              Hidden in Science mode: the harvest writes the live map
              directly (no per-run geojson). */}
          {mode !== "science" && mode !== "climatology" && (
            <RunSelector
              mode={mode}
              mapRun={mapRun}
              t={t}
              onSelect={(run) => { onSelectMapRun(run); setView("map"); }}
            />
          )}
          <button
            type="button"
            data-testid="view-toggle-audit"
            onClick={() => setView("audit")}
            className="nav-tab"
            aria-current={view === "audit" ? "true" : undefined}
          >
            <Radar {...ICON} /> {t("audit")}
          </button>
          <button
            type="button"
            data-testid="view-toggle-review"
            onClick={() => setView("review")}
            className="nav-tab"
            aria-current={view === "review" ? "true" : undefined}
          >
            <ClipboardCheck {...ICON} /> {t("review")}
          </button>
        </div>
        <a
          href={HELLOASSO_MEMBERSHIP_URL}
          target="_blank"
          rel="noopener noreferrer"
          data-testid="membership-cta"
          title={t("membershipCtaTooltip")}
          aria-label={t("membershipCta")}
          className="nav-tab border border-line rounded-md text-bio hover:text-bio"
        >
          <UserPlus {...ICON} />
          <span className="hidden 2xl:inline">{t("membershipCta")}</span>
        </a>
        <div className="nav-group m-num" role="group" aria-label="Language">
          <button
            type="button"
            data-testid="lang-toggle-en"
            onClick={() => setLang("en")}
            className="nav-tab !px-2"
            aria-pressed={lang === "en"}
            lang="en"
          >EN</button>
          <button
            type="button"
            data-testid="lang-toggle-fr"
            onClick={() => setLang("fr")}
            className="nav-tab !px-2"
            aria-pressed={lang === "fr"}
            lang="fr"
          >FR</button>
        </div>
        {isAdmin && mode !== "science" && mode !== "climatology" && (
          <button
            type="button"
            data-testid="map-show-review"
            onClick={() => onToggleShowReview && onToggleShowReview(!showReview)}
            className="nav-tab border border-line rounded-md"
            aria-pressed={showReview}
            title={t("reviewShowReview")}
          >
            <Eye {...ICON} />
            <span className="hidden 2xl:inline">{t("reviewShowReview")}</span>
          </button>
        )}
        <button
          type="button"
          data-testid="basemap-toggle-btn"
          onClick={() => setBasemap(next)}
          className="nav-icon-btn"
          title={t(titleKey)}
          aria-label={t(titleKey)}
        >
          <BasemapIcon {...ICON} />
        </button>
        <button
          type="button"
          data-testid="settings-toggle-btn"
          onClick={() => setShowSettings(!showSettings)}
          className="nav-icon-btn"
          aria-pressed={showSettings}
          title={t("settings")}
          aria-label={t("settings")}
        >
          <Settings {...ICON} />
        </button>
      </nav>
    </header>
  );
}
