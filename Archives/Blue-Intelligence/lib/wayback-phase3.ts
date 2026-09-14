/**
 * Phase 3 : Enrichissement via Claude
 * - Inférence du pays depuis l'URL (ex: Ports_-_Greece)
 * - Proposition de coordonnées via Claude pour les entrées sans lat/lng
 *
 * Déclenché via POST /api/nauticals/enrich-wayback-phase3
 */

import type Database from "better-sqlite3";
import Anthropic from "@anthropic-ai/sdk";

const COUNTRY_FROM_URL: Record<string, string> = {
  "ports_-_greece": "Greece",
  "ports_-_spain": "Spain",
  "ports_-_croatia": "Croatia",
  "ports_-_italy": "Italy",
  "ports_-_france": "France",
  "ports_-_turkey": "Turkey",
  "ports_-_norway": "Norway",
  "ports_-_portugal": "Portugal",
  "ports_-_uk": "United Kingdom",
  "ports_-_usa": "USA",
  "ports_-_canada": "Canada",
  "ports_-_australia": "Australia",
  "ports_-_new_zealand": "New Zealand",
  "ports_-_japan": "Japan",
  "ports_-_thailand": "Thailand",
  "ports_-_malaysia": "Malaysia",
  "ports_-_indonesia": "Indonesia",
  "ports_-_mexico": "Mexico",
  "ports_-_brazil": "Brazil",
  "ports_-_argentina": "Argentina",
  "ports_-_chile": "Chile",
  "ports_-_south_africa": "South Africa",
  "ports_-_egypt": "Egypt",
  "ports_-_tunisia": "Tunisia",
  "ports_-_morocco": "Morocco",
  "ports_-_malta": "Malta",
  "ports_-_cyprus": "Cyprus",
  "ports_-_iceland": "Iceland",
  "ports_-_sweden": "Sweden",
  "ports_-_finland": "Finland",
  "ports_-_estonia": "Estonia",
  "ports_-_latvia": "Latvia",
  "ports_-_lithuania": "Lithuania",
  "ports_-_poland": "Poland",
  "ports_-_germany": "Germany",
  "ports_-_netherlands": "Netherlands",
  "ports_-_belgium": "Belgium",
  "ports_-_ireland": "Ireland",
  "ports_-_slovenia": "Slovenia",
  "ports_-_montenegro": "Montenegro",
  "ports_-_albania": "Albania",
  "ports_-_bulgaria": "Bulgaria",
  "ports_-_romania": "Romania",
  "ports_-_ukraine": "Ukraine",
  "ports_-_russia": "Russia",
  "ports_-_georgia": "Georgia",
  "ports_-_israel": "Israel",
  "ports_-_lebanon": "Lebanon",
  "ports_-_syria": "Syria",
  "ports_-_uae": "United Arab Emirates",
  "ports_-_oman": "Oman",
  "ports_-_yemen": "Yemen",
  "ports_-_india": "India",
  "ports_-_sri_lanka": "Sri Lanka",
  "ports_-_maldives": "Maldives",
  "ports_-_seychelles": "Seychelles",
  "ports_-_mauritius": "Mauritius",
  "ports_-_madagascar": "Madagascar",
  "ports_-_kenya": "Kenya",
  "ports_-_tanzania": "Tanzania",
  "ports_-_mozambique": "Mozambique",
  "ports_-_caribbean": "Caribbean",
  "ports_-_bahamas": "Bahamas",
  "ports_-_bermuda": "Bermuda",
  "ports_-_fiji": "Fiji",
  "ports_-_tonga": "Tonga",
  "ports_-_samoa": "Samoa",
  "ports_-_french_polynesia": "French Polynesia",
  "ports_-_new_caledonia": "New Caledonia",
};

export function inferCountryFromWaybackUrl(sourceUrl: string): string | null {
  if (!sourceUrl) return null;
  const lower = sourceUrl.toLowerCase();
  for (const [key, country] of Object.entries(COUNTRY_FROM_URL)) {
    if (lower.includes(key)) return country;
  }
  return null;
}

export async function suggestCoordsWithClaude(
  title: string,
  description: string | null,
  country: string | null
): Promise<{ lat: number; lng: number } | null> {
  const apiKey = process.env.CLAUDE_API_KEY || process.env.ANTHROPIC_API_KEY;
  if (!apiKey) return null;
  const client = new Anthropic({ apiKey });
  try {
    const msg = await client.messages.create({
      model: "claude-sonnet-4-5-20250929",
      max_tokens: 64,
      messages: [
        {
          role: "user",
          content: `This is a maritime location (port, anchorage, etc.) from Cruisers Wiki. Suggest approximate WGS84 coordinates (latitude, longitude) as decimal degrees. Return ONLY two numbers separated by a comma, e.g. "35.1234, 14.5678". Nothing else.

Title: ${title}
Country: ${country || "unknown"}
Description: ${(description || "").slice(0, 500)}

Reply with ONLY: lat, lng`,
        },
      ],
    });
    const text = msg.content?.[0]?.type === "text" ? (msg.content[0] as { text: string }).text : "";
    const match = text.match(/(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)/);
    if (!match) return null;
    const lat = parseFloat(match[1]);
    const lng = parseFloat(match[2]);
    if (isNaN(lat) || isNaN(lng) || Math.abs(lat) > 90 || Math.abs(lng) > 180) return null;
    return { lat, lng };
  } catch {
    return null;
  }
}

export interface Phase3Result {
  countryUpdated: number;
  coordsSuggested: number;
  coordsApplied: number;
  errors: string[];
}

export async function enrichWaybackPhase3(
  db: Database.Database,
  options?: { maxCoords?: number; dryRun?: boolean }
): Promise<Phase3Result> {
  const maxCoords = options?.maxCoords ?? 100;
  const dryRun = options?.dryRun ?? false;
  const result: Phase3Result = { countryUpdated: 0, coordsSuggested: 0, coordsApplied: 0, errors: [] };

  const rows = db
    .prepare(
      `SELECT id, source_id, title, description, country, source_url FROM nauticals WHERE source = 'cruiserswiki_wayback' AND (lat IS NULL OR lng IS NULL)`
    )
    .all() as { id: number; source_id: string; title: string; description: string | null; country: string; source_url: string | null }[];

  const updateCountry = db.prepare("UPDATE nauticals SET country = ? WHERE id = ?");
  const updateCoords = db.prepare("UPDATE nauticals SET lat = ?, lng = ? WHERE id = ?");

  for (const row of rows) {
    let country = row.country || "Unknown";
    const inferred = inferCountryFromWaybackUrl(row.source_url || "");
    if (inferred && (country === "Unknown" || !country)) {
      if (!dryRun) updateCountry.run(inferred, row.id);
      result.countryUpdated++;
      country = inferred;
    }

    if (result.coordsApplied >= maxCoords) continue;
    const coord = await suggestCoordsWithClaude(row.title, row.description, country);
    if (coord) {
      result.coordsSuggested++;
      if (!dryRun) updateCoords.run(coord.lat, coord.lng, row.id);
      result.coordsApplied++;
    }
    await new Promise((r) => setTimeout(r, 300));
  }

  return result;
}
