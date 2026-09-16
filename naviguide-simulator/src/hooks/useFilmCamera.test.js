import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));

describe("caméra cinéma", () => {
  it("ne suit que si follow, sans voler le zoom", () => {
    const src = readFileSync(join(here, "useFilmCamera.js"), "utf8");
    assert.match(src, /if \(!follow\) return;/);
    assert.match(src, /keepZoom/);
    assert.doesNotMatch(src, /flyTo/);
    const beforeFollow = src.indexOf("if (!follow) return;");
    const firstSetView = src.indexOf("setView");
    assert.ok(beforeFollow > 0 && beforeFollow < firstSetView);
  });

  it("Leaflet ne saute plus entre copies du monde", () => {
    const src = readFileSync(join(here, "useSimulatorMap.js"), "utf8");
    assert.match(src, /worldCopyJump:\s*false/);
  });

  it("App n’arme le suivi que si Cinéma est allumé", () => {
    const src = readFileSync(join(here, "../App.jsx"), "utf8");
    assert.match(src, /follow: cinemaMode && cameraFollow/);
    assert.match(src, /enabled: sceneReady && cinemaMode && cameraFollow/);
    assert.match(src, /enabled: sceneReady && !customRoute/);
    assert.match(src, /drawingMode\s*\n\s*\? \[\]/);
  });
});
