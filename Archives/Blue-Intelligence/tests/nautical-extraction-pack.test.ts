/**
 * Tests du pack d'extraction nauticals.
 * Run: npx tsx tests/nautical-extraction-pack.test.ts
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import {
  applyExtractionPack,
  parseNauticalExtractionPack,
  parseCoordFromWikitext,
  DEFAULT_NAUTICAL_EXTRACTION_PACK_PATH,
  loadExtractionPack,
} from "../lib/nautical-extraction-pack.ts";

const defaultPackRaw = {
  version: "1.0.0",
  filter: {
    minRelevanceScore: 0,
    titleUrlBlacklist: [] as string[],
    titleUrlWhitelist: [] as string[],
    keywordWeights: {} as Record<string, number>,
    sectionPresenceBonus: 0,
  },
  extraction: {
    wantedSectionSubstrings: [
      "navigation",
      "entrance",
      "anchorages",
      "approach",
      "dangers",
      "warnings",
      "charts",
    ],
    dangerSectionSubstrings: ["danger", "warning"],
    maxSectionTextLength: 500,
  },
};

const WIKI_FIXTURE = `Some intro text.

== Navigation ==
Go to the harbor.

== Dangers ==
Rocks near the entrance.

{{coord|12.5|45.25}}
`;

test("parseNauticalExtractionPack accepts default-shaped object", () => {
  const p = parseNauticalExtractionPack(defaultPackRaw);
  assert.equal(p.version, "1.0.0");
  assert.equal(p.filter.minRelevanceScore, 0);
});

test("parseCoordFromWikitext decimal pair", () => {
  const c = parseCoordFromWikitext("{{coord|12.5|45.25}}");
  assert.ok(c);
  assert.equal(c!.lat, 12.5);
  assert.equal(c!.lng, 45.25);
});

test("applyExtractionPack default pack includes fixture and extracts coords", () => {
  const pack = parseNauticalExtractionPack(defaultPackRaw);
  const url = "https://www.cruiserswiki.org/wiki/Ports_-_Test/Example_Port";
  const r = applyExtractionPack(WIKI_FIXTURE, { sourceUrl: url }, pack);
  assert.equal(r.include, true);
  assert.ok(r.score >= 1);
  assert.equal(r.lat, 12.5);
  assert.equal(r.lng, 45.25);
  assert.ok(r.description?.includes("Navigation"));
  assert.ok(r.caution?.includes("Rocks"));
});

test("applyExtractionPack excludes when slug matches blacklist", () => {
  const strict = {
    ...defaultPackRaw,
    filter: {
      ...defaultPackRaw.filter,
      titleUrlBlacklist: ["sandbox_noise"],
    },
  };
  const pack = parseNauticalExtractionPack(strict);
  const url = "https://www.cruiserswiki.org/wiki/Sandbox_noise/Page";
  const r = applyExtractionPack(WIKI_FIXTURE, { sourceUrl: url }, pack);
  assert.equal(r.include, false);
  assert.ok(r.excludeReason?.startsWith("blacklist:"));
});

test("applyExtractionPack excludes when minRelevanceScore not met", () => {
  const strict = {
    ...defaultPackRaw,
    filter: {
      ...defaultPackRaw.filter,
      minRelevanceScore: 100,
    },
  };
  const pack = parseNauticalExtractionPack(strict);
  const url = "https://www.cruiserswiki.org/wiki/Ports_-_Test/Example_Port";
  const r = applyExtractionPack(WIKI_FIXTURE, { sourceUrl: url }, pack);
  assert.equal(r.include, false);
  assert.ok(r.excludeReason?.includes("below_min_score"));
});

test("loadExtractionPack reads default JSON from repo", () => {
  const p = loadExtractionPack(DEFAULT_NAUTICAL_EXTRACTION_PACK_PATH);
  assert.equal(p.version, "1.0.0");
});
