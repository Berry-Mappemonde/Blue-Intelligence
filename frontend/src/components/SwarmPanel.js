import { ChevronRight, Flag, Search } from "lucide-react";
import ProjectList from "./ProjectList";

// Number of category groups served by /api/categories (fixed taxonomy).
const LEGEND_PLACEHOLDER_ROWS = 9;

/**
 * Projects-mode side strip — same structure as the other four modes:
 * header (icon + title + count) → search → filters → list → action.
 * The clickable legend doubles as the category filter (the redundant
 * dropdown was removed).
 */
export default function SwarmPanel({ t, projects, funders, funderFilter, setFunderFilter, searchQuery, setSearchQuery, categories, categoryFilter, setCategoryFilter, onReport, onFlyTo }) {
  const legendCats = (categories || []).filter((c) => c.count > 0);

  return (
    <aside className="w-[360px] max-w-full shrink-0 flex flex-col border-r border-m-line bg-m-shell min-h-0 font-ui text-[13px] leading-[18px] text-m-fg" data-testid="swarm-panel">
      <div className="flex-1 overflow-y-auto [scrollbar-color:rgb(var(--m-line-strong))_transparent] min-h-0">
        {/* Header + search */}
        <section className="px-4 pt-4 pb-3 border-b border-m-line" data-testid="projects-panel-header">
          <div className="flex items-baseline justify-between gap-3 mb-3">
            <h2 className="text-[15px] leading-5 font-medium text-m-fg">{t("modeProjects")}</h2>
            <span className="shrink-0 text-right text-[12px] leading-4 text-m-fg3 m-num" data-testid="projects-count">
              {funders.total} {t("projects")}
            </span>
          </div>
          <div className="relative">
            <Search size={14} strokeWidth={1.75} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-m-fg3 pointer-events-none" aria-hidden="true" />
            <input
              data-testid="project-search-input"
              type="text"
              name="project-search"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder={t("searchPlaceholder")}
              aria-label={t("searchPlaceholder")}
              className="m-field !pl-8"
            />
          </div>
        </section>

        {/* Filter by organisation */}
        <section className="px-4 py-3 border-b border-m-line">
          <label className="text-[12px] leading-4 font-medium text-m-fg2 block mb-1.5" htmlFor="org-filter-select">
            {t("orgFilter")}
          </label>
          <select
            id="org-filter-select"
            data-testid="org-filter-select"
            value={funderFilter}
            onChange={(e) => setFunderFilter(e.target.value)}
            className="m-field m-select"
          >
            <option value="All">{t("allOrgs")} ({funders.total} {t("projects")})</option>
            {funders.funders.map((f) => (
              <option key={f.name} value={f.name}>{f.name} ({f.count})</option>
            ))}
          </select>
        </section>

        {/* Clickable legend = category filter */}
        <details className="m-details px-4 py-3 border-b border-m-line text-[12px] leading-4" data-testid="map-legend" open>
          <summary className="flex items-center gap-1.5 font-medium text-m-fg2 hover:text-m-fg">
            <ChevronRight size={12} strokeWidth={1.75} className="m-disclosure shrink-0" aria-hidden="true" />
            {t("legend")}
          </summary>
          <div className="m-details-body mt-1.5 grid grid-cols-1 gap-0.5">
            {/* Perf 2026-10 (CLS): until /api/categories answers, reserve the
                legend's height (9 fixed category groups) so the project list
                below does not jump down when it arrives. */}
            {legendCats.length === 0 && Array.from({ length: LEGEND_PLACEHOLDER_ROWS }, (_, i) => (
              <div key={`ph-${i}`} aria-hidden="true" data-testid="legend-placeholder"
                className="flex items-center gap-2 min-h-7 px-1.5 rounded-md">
                <span className="w-2.5 h-2.5 rounded-full shrink-0 bg-m-raised" />
                <span className="text-transparent select-none">&nbsp;</span>
              </div>
            ))}
            {legendCats.map((c) => (
              <button key={c.name} data-testid={`legend-item-${c.name}`}
                type="button"
                aria-pressed={categoryFilter === c.name}
                onClick={() => setCategoryFilter(categoryFilter === c.name ? "All" : c.name)}
                className={`flex items-center gap-2 min-h-7 px-1.5 rounded-md text-left focus-visible:outline focus-visible:outline-2 focus-visible:outline-m-accent ${categoryFilter === c.name ? "bg-m-selected text-m-fg" : "text-m-fg2 hover:bg-m-raised"}`}>
                <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ background: c.color }} aria-hidden="true" />
                <span className="truncate">{t("cat_" + c.name)}</span>
                <span className="text-m-fg3 m-num text-right shrink-0 ml-auto">{c.count}</span>
              </button>
            ))}
          </div>
        </details>

        <ProjectList t={t} projects={projects} funderFilter={funderFilter} searchQuery={searchQuery} categoryFilter={categoryFilter} onFlyTo={onFlyTo} />
      </div>

      {/* Action de pied — signaler un projet manquant */}
      <div className="shrink-0 px-4 py-3 border-t border-m-line">
        <button
          type="button"
          data-testid="report-project-btn"
          onClick={onReport}
          className="m-btn m-btn-secondary w-full"
        >
          <Flag size={14} strokeWidth={1.75} aria-hidden="true" /> {t("reportBtn")}
        </button>
      </div>
    </aside>
  );
}
