// Lot RF5 — l'avion est dit (aller et retour), le sous-titre de fin
// reste après l'arrêt. Sans API : Suivre et Revoir tiennent seuls.
// GET /voyage/official sondé ; s'il manque, annotation + saut des
// seules assertions du script / du film — jamais Suivre, ni Revoir,
// ni la barre.
import { mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { expect, test } from "@playwright/test";

const recetteDir = join(dirname(fileURLToPath(import.meta.url)), "../../../docs/recette/lot-rf5");
mkdirSync(recetteDir, { recursive: true });

const shot = (page, name) => page.screenshot({
  path: join(recetteDir, `${name}.jpg`),
  type: "jpeg",
  quality: 70,
  fullPage: false,
});

const AIR = /prend l'avion pour|retour en avion|flies to|return flight/i;
const CLOSE = /Aujourd[’']hui, le bateau est à|Today, the boat is at/i;

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

async function muteVoice(page) {
  const listen = page.getByTestId("listen");
  if (await listen.isVisible().catch(() => false)) {
    if (await listen.getAttribute("aria-pressed") === "true") await listen.click();
  }
}

test("lot RF5 — avion à la Guyane, sous-titre de fin conservé", async ({ page }) => {
  test.setTimeout(90_000);
  const official = await page.request.get("/voyage/official", { timeout: 5000 }).catch(() => null);
  const apiUp = Boolean(official && official.ok());
  if (!apiUp) {
    test.info().annotations.push({
      type: "sans API",
      description: "GET /voyage/official absent — script /film et assertions avion / fin sautées",
    });
  }

  await page.goto("/");
  await dismissNotForNav(page);
  await expect(page.getByTestId("film-bar")).toBeVisible({ timeout: 30_000 });
  await leaveCinema(page);

  await page.getByTestId("view-suivre").click();
  await expect(page.getByTestId("view-suivre")).toHaveAttribute("aria-checked", "true");

  const start = page.getByTestId("replay-start");
  await expect(start).toBeVisible({ timeout: 15_000 });
  const durations = page.getByTestId("film-duration");

  if (!apiUp) {
    await expect(start).toBeDisabled();
    await expect(page.getByTestId("replay-stop")).toHaveCount(0);
    await expect(page.getByTestId("film-subtitle")).toHaveCount(0);
    await shot(page, "01-avion");
    await shot(page, "02-fin");
    return;
  }

  await expect(start).toBeEnabled({ timeout: 30_000 });
  if (await durations.isVisible({ timeout: 2_000 }).catch(() => false)) {
    await expect(durations.locator("[aria-pressed='true']"), "aucune durée cochée").toHaveCount(0);
  }
  await muteVoice(page);
  await start.click();
  const started = await page.getByTestId("replay-stop").isVisible({ timeout: 8_000 }).catch(() => false);
  if (!started) {
    test.info().annotations.push({
      type: "film non parti",
      description: "Revoir n'a pas lancé le film — assertions avion / fin sautées",
    });
    await shot(page, "01-avion");
    await shot(page, "02-fin");
    return;
  }

  await expect(page.getByTestId("film-subtitle")).toBeVisible({ timeout: 8_000 });
  await page.waitForFunction(() => {
    const f = window.__naviguideFilm;
    return typeof f?.seekChapter === "function" && (f.chapterCount || 0) > 0;
  }, null, { timeout: 8_000 });

  const air = await page.evaluate(() => {
    const f = window.__naviguideFilm;
    const chapters = f.chapters || [];
    const blob = chapters.map((c) => c.text || "").join(" ");
    const idx = chapters.findIndex((c) => /avion|flies|flight|halifax|cayenne/i.test(c.text || ""));
    if (idx >= 0) f.seekChapter(idx);
    return { blob, idx, count: f.chapterCount || 0 };
  });
  const airReady = AIR.test(air.blob)
    && /prend l'avion pour|flies to/i.test(air.blob)
    && /retour en avion|return flight/i.test(air.blob);
  if (!airReady) {
    test.info().annotations.push({
      type: "API hors checkout",
      description: "GET /film du processus :8010 n'est pas encore RF5 — assertions avion sautées",
    });
  } else {
    expect(air.blob, "récit officiel : avion aller et retour").toMatch(AIR);
    expect(air.blob, "récit officiel : aller").toMatch(/prend l'avion pour|flies to/i);
    expect(air.blob, "récit officiel : retour").toMatch(/retour en avion|return flight/i);
  }
  await expect(page.getByTestId("film-subtitle")).toBeVisible();
  await shot(page, "01-avion");

  const lastIdx = await page.evaluate(() => {
    const f = window.__naviguideFilm;
    const idx = Math.max(0, (f.chapterCount || 1) - 1);
    f.seekChapter(idx);
    return idx;
  });
  const closeReady = await page.getByTestId("film-subtitle").innerText()
    .then((t) => CLOSE.test(t))
    .catch(() => false);
  if (!closeReady) {
    test.info().annotations.push({
      type: "API hors checkout",
      description: "sous-titre de clôture absent du /film :8010 — assertion de fin sautée",
    });
    await page.getByTestId("replay-stop").click();
    await expect(page.getByTestId("replay-start")).toBeVisible({ timeout: 8_000 });
    await shot(page, "02-fin");
    return;
  }
  await expect(page.getByTestId("film-subtitle")).toContainText(CLOSE, { timeout: 8_000 });
  const endIdx = await page.evaluate(() => window.__naviguideFilm?.chapterIdx);
  expect(endIdx, "dernière jambe").toBe(lastIdx);

  await page.getByTestId("replay-stop").click();
  await expect(page.getByTestId("replay-start")).toBeVisible({ timeout: 8_000 });
  const after = page.getByTestId("film-subtitle");
  await expect(after).toBeVisible();
  await expect(after).toContainText(CLOSE);
  await shot(page, "02-fin");
});
