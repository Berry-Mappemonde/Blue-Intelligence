import { ExternalLink } from "lucide-react";

// Per-project donate buttons were removed; membership happens via the HelloAsso
// CTA in the header (Berry-Mappemonde association).
export default function ProjectList({ t, projects, funderFilter, searchQuery, categoryFilter, onFlyTo }) {
  const q = (searchQuery || "").toLowerCase();
  const features = (projects.features || []).filter(
    (f) => (funderFilter === "All" || (f.properties.funder || "").includes(funderFilter)) &&
      (categoryFilter === "All" || f.properties.category_group === categoryFilter) &&
      (!q || `${f.properties.title} ${f.properties.description} ${f.properties.funder} ${f.properties.location || ""}`.toLowerCase().includes(q))
  );

  return (
    <section className="py-3" data-testid="project-list">
      <p className="flex items-baseline justify-between gap-3 px-4 mb-2 text-[12px] leading-4 font-medium text-m-fg2">
        {t("projectList")} <span className="text-m-fg3 m-num text-right">{features.length}</span>
      </p>
      {features.length === 0 && (
        <p className="px-4 py-3 text-[13px] leading-[18px] text-m-fg3">{t("noProjects")}</p>
      )}
      <div className="divide-y divide-m-line-soft">
        {features.slice(0, 100).map((f) => (
          // Row button and external link are siblings (no interactive nesting);
          // same layout as before: title, funder, link icon at the end of line 2.
          // Keyboard order: row, then link.
          <div key={f.properties.id} className="relative hover:bg-m-raised" data-testid={`project-row-${f.properties.id}`}>
            <button
              type="button"
              data-testid={`project-item-${f.properties.id}`}
              onClick={() => {
                const [lon, lat] = f.geometry?.coordinates || [];
                if (onFlyTo && lat != null && lon != null) onFlyTo(f.properties.id, lat, lon);
              }}
              className="w-full text-left pl-4 pr-10 py-2.5 focus-visible:outline focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-m-accent"
            >
              <p className="text-[13px] leading-[18px] font-medium text-m-fg break-words">{f.properties.title}</p>
              <span className="block mt-1 text-[12px] leading-4 text-m-fg3 truncate">{f.properties.funder}</span>
            </button>
            {f.properties.url ? (
              <a
                href={f.properties.url}
                target="_blank"
                rel="noreferrer"
                aria-label={`${f.properties.title}: ${t("projectOpenPage")}`}
                title={t("projectOpenPage")}
                className="absolute right-4 bottom-[11px] shrink-0 text-m-fg3 hover:text-m-fg rounded-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-m-accent"
              >
                <ExternalLink size={14} strokeWidth={1.75} />
              </a>
            ) : null}
          </div>
        ))}
      </div>
    </section>
  );
}
