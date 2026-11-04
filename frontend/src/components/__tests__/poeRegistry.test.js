import { mergeVerifyIntoFiche, portKey } from "../poeRegistry";
import cases from "./portKeyCases.json";

describe("portKey", () => {
  it("matches the backend port_key on every shared case", () => {
    const mismatches = cases.filter((c) => portKey(c.name) !== c.key);
    expect(mismatches.map((c) => [c.name, portKey(c.name), c.key])).toEqual([]);
  });

  it("removes one facility word at each end, like the backend", () => {
    expect(portKey("Marina de Port Vauban")).toBe("port vauban");
    expect(portKey("Port of the Isles")).toBe("the isles");
  });

  it("drops a possessive written with any apostrophe", () => {
    expect(portKey("St George‘s")).toBe("saint george");
    expect(portKey("St George´s")).toBe("saint george");
    expect(portKey("Port of St. George’s")).toBe(portKey("St. George's"));
  });
});

describe("mergeVerifyIntoFiche", () => {
  it("matches a verified port to its fiche port by port key", () => {
    const fiche = { ports: [{ name: "St. George's", confidence: 40 }] };
    const result = {
      validated_ports: [{ name: "Port of St. George’s", confidence: 67, verdict: "pass", registry: { tier: "tier1" } }],
    };
    const merged = mergeVerifyIntoFiche(fiche, result);
    expect(merged.ports).toHaveLength(1);
    expect(merged.ports[0]).toMatchObject({ name: "St. George's", confidence: 67, verdict: "pass" });
  });
});
