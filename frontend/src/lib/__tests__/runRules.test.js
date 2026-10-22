import { coerceValue, inInterval, isIntRule } from "../runRules";

// Représentation réelle sur le fil : `JSON.stringify` écrit 15.0 en 15 et
// `JSON.parse` efface ensuite toute distinction. Seul `numeric` survit au
// voyage, ce qui justifie qu'il soit porté par le catalogue.
const wire = (rule) => JSON.parse(JSON.stringify(rule));

// Valeur *et* bornes entières : toute inférence par Number.isInteger ou par
// l'intervalle les classerait à tort en entier (cf. relecture de la PR).
const FLOAT_RULES = [
  ["projects.max_inland_km", 15.0, [8.0, 25.0]],
  ["formalities.inland_river_max_km", 400.0, [200.0, 600.0]],
  ["marinas.max_bbox_span_nm", 500.0, [100.0, 800.0]],
  ["formalities.wpi_proximity_km", 1.0, [0.5, 2.0]],
];

const INT_RULES = [
  ["formalities.max_ports_per_zone", 150, [50, 400]],
  ["projects.max_partner_orgs", 15, [3, 50]],
];

describe("isIntRule lit le type explicite du catalogue", () => {
  FLOAT_RULES.forEach(([id, value, interval]) => {
    it(`${id} reste flottant malgré valeur et bornes entières`, () => {
      const rule = wire({ id, value, interval, numeric: "float" });
      expect(isIntRule(rule)).toBe(false);
    });
  });

  INT_RULES.forEach(([id, value, interval]) => {
    it(`${id} est entier`, () => {
      const rule = wire({ id, value, interval, numeric: "int" });
      expect(isIntRule(rule)).toBe(true);
    });
  });

  it("sans numeric, retombe sur la valeur (comportement d'avant)", () => {
    expect(isIntRule(wire({ id: "x", value: 15.0, interval: [8.0, 25.0] }))).toBe(true);
    expect(isIntRule(wire({ id: "y", value: 1.5, interval: [0.5, 2.0] }))).toBe(false);
  });

  it("un booléen n'est jamais une règle numérique", () => {
    expect(isIntRule(wire({ id: "b", value: true, numeric: null }))).toBe(false);
  });
});

describe("coerceValue ne tronque plus les distances", () => {
  FLOAT_RULES.forEach(([id, value, interval]) => {
    it(`${id} conserve la partie fractionnaire`, () => {
      const rule = wire({ id, value, interval, numeric: "float" });
      const raw = String(value + 0.5);
      const got = coerceValue(rule, raw);
      expect(got).toBeCloseTo(value + 0.5, 10);
      expect(inInterval(rule, got)).toBe(true);
    });
  });

  it("wpi_proximity_km garde 0.5 et 1.5 au lieu de les ramener à 0 et 1", () => {
    const rule = wire({
      id: "formalities.wpi_proximity_km", value: 1.0,
      interval: [0.5, 2.0], numeric: "float",
    });
    expect(coerceValue(rule, "0.5")).toBe(0.5);
    expect(coerceValue(rule, "1.5")).toBe(1.5);
    expect(inInterval(rule, coerceValue(rule, "0.5"))).toBe(true);
  });

  it("une règle entière reste tronquée en entier", () => {
    const rule = wire({
      id: "formalities.max_ports_per_zone", value: 150,
      interval: [50, 400], numeric: "int",
    });
    expect(coerceValue(rule, "7")).toBe(7);
    expect(isIntRule(rule)).toBe(true);
  });
});
