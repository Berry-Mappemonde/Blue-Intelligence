// Lot RF1 — plus de 400 /advice au parcours nominal. Sans API : barre film,
// Suivre / Simulation / Tracer et l'onglet Revue tiennent seuls ; aucune
// assertion d'API. GET /voyage/official sondé ; s'il manque, annotation +
// saut des seules assertions /advice et /plan-review — jamais les modes,
// ni l'onglet, ni l'absence de ligne rouge advice côté page.
import { mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { expect, test } from "@playwright/test";

const recetteDir = join(dirname(fileURLToPath(import.meta.url)), "../../../docs/recette/lot-rf1");
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

function isAdviceUrl(url) {
  return /\/voyage\/official\/advice(?:\?|$)/.test(url);
}

test("lot RF1 — aucune ligne rouge advice, revue inchangée", async ({ page }) => {
  test.setTimeout(90_000);
  const official = await page.request.get("/voyage/official", { timeout: 5000 }).catch(() => null);
  const apiUp = Boolean(official && official.ok());
  if (!apiUp) {
    test.info().annotations.push({
      type: "sans API",
      description: "GET /voyage/official absent — assertions /advice et /plan-review sautées",
    });
  }

  const adviceBad = [];
  page.on("response", (res) => {
    if (!isAdviceUrl(res.url())) return;
    if (res.status() >= 400) adviceBad.push(`${res.status()} ${res.url()}`);
  });

  await page.goto("/");
  await dismissNotForNav(page);
  await expect(page.getByTestId("film-bar")).toBeVisible({ timeout: 30_000 });
  await leaveCinema(page);

  await page.getByTestId("view-suivre").click();
  await expect(page.getByTestId("view-suivre")).toHaveAttribute("aria-checked", "true");
  await expect(page.getByTestId("film-bar")).toBeVisible();
  await showLeftPanel(page);
  const tab = page.getByTestId("ici-tab-review");
  await expect(tab).toBeVisible({ timeout: 10_000 });
  await tab.click();
  await expect(page.getByTestId("ici-review-slot")).toBeVisible();
  await expect(page.getByTestId("plan-review")).toBeVisible();
  await expect(page.getByTestId("plan-review-leg").first()).toBeVisible({ timeout: 10_000 });
  await page.waitForTimeout(1200);
  await shot(page, "01-console");

  await page.getByTestId("view-simulation").click();
  await expect(page.getByTestId("view-simulation")).toHaveAttribute("aria-checked", "true");
  await expect(page.getByTestId("film-bar")).toBeVisible();
  await expect(page.getByTestId("ici-tab-review")).toBeVisible();
  await page.waitForTimeout(800);

  const draw = page.getByRole("button", { name: /Berry-Mappemonde.*Tracer votre propre route|Draw your own route/i });
  await expect(draw).toBeVisible({ timeout: 15_000 });
  await draw.scrollIntoViewIfNeeded();
  await draw.click({ force: true });
  await expect(page.getByTestId("drawing-box")).toBeVisible({ timeout: 15_000 });
  await page.waitForTimeout(400);

  expect(adviceBad, `advice 4xx/5xx : ${adviceBad.join(" | ")}`).toEqual([]);

  if (!apiUp) return;

  const reviewRes = await page.request.get("/voyage/official/plan-review", { timeout: 12_000 }).catch(() => null);
  if (!reviewRes || !reviewRes.ok()) {
    test.info().annotations.push({
      type: "sans plan-review",
      description: `GET /voyage/official/plan-review → ${reviewRes ? reviewRes.status() : "erreur"} — indice revue non joué`,
    });
    return;
  }
  const review = await reviewRes.json();
  const n = Array.isArray(review?.legs) ? review.legs.length : 0;
  const idx = n > 0 ? n - 1 : 0;
  const adviceRes = await page.request.get(`/voyage/official/advice?leg=${idx}`, { timeout: 8000 }).catch(() => null);
  expect(adviceRes, "GET /advice répond").toBeTruthy();
  expect(adviceRes.status(), "advice indice revue sans 4xx").toBeLessThan(400);
  const body = await adviceRes.json();
  expect(body.status).toMatch(/^(pending|done|unavailable)$/);

  const missing = await page.request.get("/voyage/official/advice?leg=399", { timeout: 8000 });
  expect(missing.status()).toBe(200);
  expect((await missing.json()).status).toBe("unavailable");
});
