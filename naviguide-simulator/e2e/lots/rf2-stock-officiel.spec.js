// Lot RF2 — voyage officiel servi depuis le stock. Sans API : barre film,
// Suivre, Journal et Revue tiennent seuls. GET /voyage/official sondé ;
// s'il manque, annotation + saut des seules assertions d'API — jamais les
// modes ni l'onglet Journal.
import { mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { expect, test } from "@playwright/test";

const recetteDir = join(dirname(fileURLToPath(import.meta.url)), "../../../docs/recette/lot-rf2");
mkdirSync(recetteDir, { recursive: true });

const shot = (page, name) => page.screenshot({
  path: join(recetteDir, `${name}.jpg`),
  type: "jpeg",
  quality: 70,
  fullPage: false,
});

async function dismissNotForNav(page) {
  const ok = page.getByRole("button", { name: /compris|j.ai compris|ok|continuer|accepter|understand|accept/i }).first();
  if (await ok.isVisible({ timeout: 3000 }).catch(() => false)) {
    const ack = page.getByTestId("not-for-nav-ack");
    if (await ack.isVisible().catch(() => false)) await ack.check();
    await ok.click();
  }
}

async function leaveCinema(page) {
  const cinema = page.getByRole("button", { name: /^(cinéma|cinema)$/i });
  if (!(await cinema.isVisible().catch(() => false))) return;
  const on = /bg-cyan-700/.test((await cinema.getAttribute("class")) || "");
  if (on) await cinema.click();
}

async function showLeftPanel(page) {
  await leaveCinema(page);
  const box = page.getByTestId("ici-maintenant");
  if (await box.isVisible({ timeout: 2_000 }).catch(() => false)) return;
  const toggle = page.locator(".naviguide-sidebar-toggle--left");
  if (await toggle.isVisible().catch(() => false)) await toggle.click();
  await expect(box).toBeVisible({ timeout: 15_000 });
}

test("lot RF2 — Journal, fourchette et revue depuis le stock", async ({ page }) => {
  test.setTimeout(90_000);
  const official = await page.request.get("/voyage/official", { timeout: 5000 }).catch(() => null);
  const apiUp = Boolean(official && official.ok());
  if (!apiUp) {
    test.info().annotations.push({
      type: "sans API",
      description: "GET /voyage/official absent — assertions stock sautées",
    });
  }

  await page.goto("/");
  await dismissNotForNav(page);
  await expect(page.getByTestId("film-bar")).toBeVisible({ timeout: 30_000 });
  await leaveCinema(page);

  await page.getByTestId("view-suivre").click();
  await expect(page.getByTestId("view-suivre")).toHaveAttribute("aria-checked", "true");
  await expect(page.getByTestId("film-bar")).toBeVisible();
  await showLeftPanel(page);

  const journalTab = page.getByTestId("ici-tab-journal");
  await expect(journalTab).toBeVisible({ timeout: 10_000 });
  await journalTab.click();
  await expect(page.getByTestId("ici-maintenant")).toBeVisible();

  const reviewTab = page.getByTestId("ici-tab-review");
  await expect(reviewTab).toBeVisible();
  await reviewTab.click();
  await expect(page.getByTestId("ici-review-slot")).toBeAttached({ timeout: 8_000 });

  await journalTab.click();

  if (!apiUp) {
    await page.waitForTimeout(400);
    await shot(page, "01-journal-immediat");
    return;
  }

  const moments = await page.request.get("/voyage/official/moments", { timeout: 8000 }).catch(() => null);
  const eta = await page.request.get("/voyage/official/eta?stop=Noum%C3%A9a", { timeout: 8000 }).catch(() => null);
  const review = await page.request.get("/voyage/official/plan-review", { timeout: 8000 }).catch(() => null);
  const film = await page.request.get("/voyage/official/film?lang=fr&seconds=150", { timeout: 8000 }).catch(() => null);

  expect(moments, "GET /moments répond").toBeTruthy();
  expect(moments.status(), "moments sans 5xx").toBeLessThan(500);
  expect(eta, "GET /eta répond").toBeTruthy();
  expect(eta.status(), "eta sans 5xx").toBeLessThan(500);
  expect(review, "GET /plan-review répond").toBeTruthy();
  expect(review.status(), "plan-review sans 5xx").toBeLessThan(500);
  expect(film, "GET /film répond").toBeTruthy();
  expect(film.status(), "film sans 5xx").toBeLessThan(500);

  const momentsBody = await moments.json();
  expect(momentsBody.status || "ready").toMatch(/^(ready|preparing)$/);
  const usable = (momentsBody.moments || []).filter((row) => row && row.t && row.signature);
  if (momentsBody.status !== "preparing" && usable.length) {
    await expect(page.getByTestId("ici-journal-entry").first()).toBeVisible({ timeout: 8_000 });
    await expect(page.getByTestId("ici-journal-entry").first()).toContainText(/Départ|Saint-Maur|La Rochelle/i);
  }

  const etaBody = await eta.json();
  expect(Number(etaBody.members || 0) >= 0).toBeTruthy();
  const reviewBody = await review.json();
  expect(Array.isArray(reviewBody.legs)).toBeTruthy();

  await shot(page, "01-journal-immediat");
});
