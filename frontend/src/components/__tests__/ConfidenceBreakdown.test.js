import { breakdownModel } from "../ConfidenceBreakdown";

// Forme réelle renvoyée par /api/poe/ports (ports_to_geojson).
const PARTS = { source: 30, reading: 25, map: 25, external: 8 };
const REASONS = ["source d'État", "dans la ZEE, géocodeurs d'accord"];
const REASONS_EN = ["government source", "inside the EEZ, geocoders agree"];

describe("breakdownModel — ordre et total", () => {
  it("suit l'ordre du cahier des charges: Source / Reading / Map / External", () => {
    const { entries } = breakdownModel(PARTS, [], [], "fr");
    expect(entries.map((e) => e.key)).toEqual(["source", "reading", "map", "external"]);
  });

  it("totalise les points obtenus", () => {
    expect(breakdownModel(PARTS, [], [], "fr").total).toBe(88);
  });

  it("écarte les postes à zéro, jamais de segment vide", () => {
    const { entries } = breakdownModel({ source: 30, reading: 0, map: 0, external: 4 }, [], [], "fr");
    expect(entries.map((e) => e.key)).toEqual(["source", "external"]);
  });

  it("reste stable sans parties ni raisons", () => {
    const m = breakdownModel(undefined, undefined, undefined, "fr");
    expect(m.entries).toEqual([]);
    expect(m.total).toBe(0);
    expect(m.list).toEqual([]);
  });

  it("n'invente rien pour une valeur absente ou non numérique", () => {
    const { entries, total } = breakdownModel({ source: null, map: "x", reading: 10 }, [], [], "fr");
    expect(entries.map((e) => e.key)).toEqual(["reading"]);
    expect(total).toBe(10);
  });

  it("ramène une valeur négative à zéro", () => {
    const { total } = breakdownModel({ source: -5, map: 12 }, [], [], "fr");
    expect(total).toBe(12);
  });
});

describe("breakdownModel — langue des raisons", () => {
  it("en anglais, prend la traduction fournie par l'API", () => {
    expect(breakdownModel(PARTS, REASONS, REASONS_EN, "en").list).toEqual(REASONS_EN);
  });

  it("en français, garde le libellé d'origine", () => {
    expect(breakdownModel(PARTS, REASONS, REASONS_EN, "fr").list).toEqual(REASONS);
  });

  it("sans traduction anglaise, retombe sur une liste vide plutôt que d'inventer", () => {
    expect(breakdownModel(PARTS, REASONS, undefined, "en").list).toEqual([]);
  });
});
