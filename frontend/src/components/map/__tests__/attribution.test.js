import { installAttributionDedupe, uniqueAttributionItems } from "../attribution";

describe("uniqueAttributionItems", () => {
  test("each provider once, first-seen order, markup kept", () => {
    const items = uniqueAttributionItems([
      "&copy; Esri &copy; OpenStreetMap contributors",
      "© OpenStreetMap contributors",
      '© <a href="https://openwaters.io/charts/seamap">Open Waters: Seamap</a> (CC-BY 4.0) · © OpenStreetMap contributors · © Mapterhorn · Seascape',
      "© Open Waters", "© Open Waters", "© Open Waters",
    ]);
    expect(items).toEqual([
      "&copy; Esri",
      "&copy; OpenStreetMap contributors",
      '© <a href="https://openwaters.io/charts/seamap">Open Waters: Seamap</a> (CC-BY 4.0)',
      "© Mapterhorn",
      "Seascape",
      "© Open Waters",
    ]);
  });

  test("empty and blank strings are ignored", () => {
    expect(uniqueAttributionItems(["", null, " , "])).toEqual([]);
  });
});

describe("installAttributionDedupe", () => {
  test("renders prefix and unique items with Leaflet's separator, once per control", () => {
    const control = {
      _map: {},
      _container: { innerHTML: "" },
      _attributions: { "© A": 1, "© A, © B": 2, "© C": 0 },
      options: { prefix: "Leaflet" },
    };
    installAttributionDedupe(control);
    expect(control._container.innerHTML).toBe('Leaflet <span aria-hidden="true">|</span> © A, © B');
    const update = control._update;
    installAttributionDedupe(control);
    expect(control._update).toBe(update);
  });
});
