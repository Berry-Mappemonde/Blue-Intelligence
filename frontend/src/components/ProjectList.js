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
          <button
            type="button"
            key={f.properties.id}
            data-testid={`project-item-${f.properties.id}`}
            onClick={() => {
              const [lon, lat] = f.geometry?.coordinates || [];
              if (onFlyTo && lat != null && lon != null) onFlyTo(f.properties.id, lat, lon);
            }}
            className="w-full text-left px-4 py-2.5 hover:bg-m-raised focus-visible:outline focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-m-accent"
          >
            <p className="text-[13px] leading-[18px] font-medium text-m-fg break-words">{f.properties.title}</p>
            <div className="flex items-center justify-between gap-3 mt-1">
              <span className="text-[12px] leading-4 text-m-fg3 truncate">{f.properties.funder}</span>
              <a href={f.properties.url} target="_blank" rel="noreferrer"
                onClick={(e) => e.stopPropagation()}
                aria-label={f.properties.title}
                className="shrink-0 text-m-fg3 hover:text-m-fg focus-visible:outline focus-visible:outline-2 focus-visible:outline-m-accent">
                <ExternalLink size={14} strokeWidth={1.75} />
              </a>
            </div>
          </button>
        ))}
      </div>
    </section>
  );
}
