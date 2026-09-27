// Lot RF4 — console vierge pendant le film : le bateau du film ne
// déclenche plus GET /ici, /ici/moment, /eta, /advice. Sans API : Suivre
// et Revoir tiennent seuls. GET /voyage/official sondé ; s'il manque,
// annotation + saut des seules assertions d'API et du film — jamais les
// modes ni la barre.
import { mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { expect, test } from "@playwright/test";

const recetteDir = join(dirname(fileURLToPath(import.meta.url)), "../../../docs/recette/lot-rf4");
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

async function muteVoice(page) {
  const listen = page.getByTestId("listen");
  if (await listen.isVisible().catch(() => false)) {
    if (await listen.getAttribute("aria-pressed") === "true") await listen.click();
  }
}

function classifyLiveHook(url) {
  if (/\/ici\/moment/.test(url)) return "moment";
  if (/\/voyage\/official\/eta/.test(url)) return "eta";
  if (/\/voyage\/official\/advice/.test(url)) return "advice";
  if (/\/ici(?:\?|$)/.test(url)) return /[?&]thin=1/.test(url) ? "iciThin" : "ici";
  return null;
}

test("lot RF4 — aucune rafale /ici pendant le film", async ({ page }) => {
  test.setTimeout(90_000);
  const official = await page.request.get("/voyage/official", { timeout: 5000 }).catch(() => null);
  const apiUp = Boolean(official && official.ok());
  if (!apiUp) {
    test.info().annotations.push({
      type: "sans API",
      description: "GET /voyage/official absent — assertions film /ici /eta sautées",
    });
  }

  const pageErrors = [];
  page.on("pageerror", (err) => pageErrors.push(String(err)));

  await page.goto("/");
  await dismissNotForNav(page);
  await expect(page.getByTestId("film-bar")).toBeVisible({ timeout: 30_000 });
  await leaveCinema(page);

  await page.getByTestId("view-suivre").click();
  await expect(page.getByTestId("view-suivre")).toHaveAttribute("aria-checked", "true");
  await expect(page.getByTestId("film-bar")).toBeVisible();

  const start = page.getByTestId("replay-start");
  await expect(start).toBeVisible({ timeout: 15_000 });

  if (!apiUp) {
    await showLeftPanel(page);
    await expect(page.getByTestId("ici-maintenant")).toBeVisible();
    await expect(start).toBeDisabled();
    await expect(page.getByTestId("replay-stop")).toHaveCount(0);
    await shot(page, "01-console-film");
    expect(pageErrors, `erreurs page : ${pageErrors.join(" | ")}`).toEqual([]);
    return;
  }

  await expect(start).toBeEnabled({ timeout: 30_000 });
  const durations = page.getByTestId("film-duration");
  await expect(durations).toBeVisible();
  await expect(durations.locator("[aria-pressed='true']"), "aucune durée cochée").toHaveCount(0);
  await muteVoice(page);
  await page.waitForTimeout(1200);

  let phase = "pre";
  const during = { ici: 0, iciThin: 0, moment: 0, eta: 0, advice: 0 };
  const after = { ici: 0, iciThin: 0, moment: 0, eta: 0, advice: 0 };
  page.on("request", (req) => {
    const kind = classifyLiveHook(req.url());
    if (!kind) return;
    if (phase === "film") during[kind] += 1;
    if (phase === "after") after[kind] += 1;
  });

  phase = "film";
  await start.click();
  const started = await page.getByTestId("replay-stop").isVisible({ timeout: 8_000 }).catch(() => false);
  if (!started) {
    test.info().annotations.push({
      type: "film non parti",
      description: "Revoir n'a pas lancé le film (script officiel sans tA/tB) — assertions rafale sautées",
    });
    await showLeftPanel(page);
    await expect(page.getByTestId("ici-maintenant")).toBeVisible();
    await shot(page, "01-console-film");
    expect(pageErrors, `erreurs page : ${pageErrors.join(" | ")}`).toEqual([]);
    return;
  }

  await expect(page.getByTestId("film-subtitle")).toBeVisible({ timeout: 8_000 });
  await showLeftPanel(page);
  await page.waitForTimeout(5000);
  expect(during.ici, `GET /ici pendant le film : ${during.ici}`).toBe(0);
  expect(during.iciThin, `GET /ici?thin pendant le film : ${during.iciThin}`).toBe(0);
  expect(during.moment, `GET /ici/moment pendant le film : ${during.moment}`).toBe(0);
  expect(during.eta, `GET /eta pendant le film : ${during.eta}`).toBe(0);
  expect(during.advice, `GET /advice pendant le film : ${during.advice}`).toBe(0);
  await shot(page, "01-console-film");

  phase = "after";
  await page.getByTestId("replay-stop").click();
  await expect(page.getByTestId("replay-start")).toBeVisible({ timeout: 8_000 });
  await expect(page.getByTestId("ici-maintenant")).toBeVisible();
  await page.waitForTimeout(2000);
  expect(after.ici, `rattrapage /ici après Stop : ${after.ici}`).toBeLessThanOrEqual(1);
  expect(after.eta, `rattrapage /eta après Stop : ${after.eta}`).toBeLessThanOrEqual(1);
  expect(after.advice, `rattrapage /advice après Stop : ${after.advice}`).toBeLessThanOrEqual(1);
  expect(pageErrors, `erreurs page : ${pageErrors.join(" | ")}`).toEqual([]);
});
