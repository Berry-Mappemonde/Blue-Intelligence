/**
 * Fetch Cruisers Wiki via FlareSolverr (priorité 1), Proxy, TinyFish, ou Direct.
 * Utilisable par le serveur et les scripts standalone (ex: cruiserswiki-structure).
 */
export type CruisersWikiFetchResult = { text: string; status: number };

export type CruisersWikiFetchOptions = {
  /** Fetcher optionnel à essayer après Proxy, avant TinyFish (ex: Playwright) */
  extraFetcher?: (url: string) => Promise<CruisersWikiFetchResult | null>;
};

const FLARESOLVERR_URL = process.env.FLARESOLVERR_URL || "http://localhost:8191/v1";
const HEADERS: Record<string, string> = {
  "User-Agent": "BlueIntelligence/1.0 (Maritime OSINT; +https://github.com/blue-intelligence)",
  Accept: "application/json",
};

const TINYFISH_GOAL =
  "This URL returns JSON from a MediaWiki API. Navigate to it and extract the entire response body as raw text. Return it in a field named 'json' - do not parse or modify, copy exactly.";

const PROXY_RETRY_502 = 2;
const PROXY_RETRY_DELAY_MS = 3000;
const RETRY_502 = 3;
const RETRY_DELAY_MS = 2000;

function sleep(ms: number): Promise<void> {
  return new Promise((r) => setTimeout(r, ms));
}

export function isCruisersWikiValidJson(text: string): boolean {
  const t = text.trim();
  return (t.startsWith("{") || t.startsWith("[")) && !t.startsWith("<");
}

export function getCruisersWikiProxyBase(): string | null {
  const custom = process.env.CRUISERSWIKI_PROXY_URL?.trim();
  if (custom)
    return custom.endsWith("=") || custom.includes("url=")
      ? custom
      : custom + (custom.includes("?") ? "&" : "?") + "url=";
  const scrapeDo =
    process.env["SCRAPE.DO_API_KEY"] ||
    process.env.SCRAPE_DO_API_KEY ||
    process.env.SCRAPEDO_API_KEY ||
    process.env.SCRAPEDO_TOKEN;
  if (scrapeDo) return `https://api.scrape.do/?token=${scrapeDo}&url=`;
  return null;
}

async function fetchViaFlareSolverr(url: string): Promise<CruisersWikiFetchResult | null> {
  try {
    const res = await fetch(FLARESOLVERR_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ cmd: "request.get", url, maxTimeout: 60000 }),
      signal: AbortSignal.timeout(90000),
    });
    if (!res.ok) return null;
    const data = await res.json();
    if (data.status !== "ok" || !data.solution) return null;
    const response = data.solution.response ?? data.solution.html ?? data.solution.body;
    if (!response || typeof response !== "string") return null;
    if (!isCruisersWikiValidJson(response)) return null;
    return { text: response, status: 200 };
  } catch {
    return null;
  }
}

async function fetchViaProxy(url: string): Promise<CruisersWikiFetchResult | null> {
  const proxyBase = getCruisersWikiProxyBase();
  if (!proxyBase) return null;
  for (let attempt = 1; attempt <= PROXY_RETRY_502; attempt++) {
    try {
      const res = await fetch(proxyBase + encodeURIComponent(url), { headers: HEADERS });
      const text = await res.text();
      if (res.status >= 200 && res.status < 400) return { text, status: res.status };
      if (res.status === 502 && attempt < PROXY_RETRY_502) {
        await sleep(PROXY_RETRY_DELAY_MS);
        continue;
      }
      return { text, status: res.status };
    } catch {
      if (attempt < PROXY_RETRY_502) await sleep(PROXY_RETRY_DELAY_MS);
      else return null;
    }
  }
  return null;
}

async function fetchViaTinyFish(url: string): Promise<CruisersWikiFetchResult | null> {
  const apiKey = process.env.TINYFISH_API_KEY;
  if (!apiKey) return null;
  try {
    const res = await fetch("https://agent.tinyfish.ai/v1/automation/run-async", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-API-Key": apiKey },
      body: JSON.stringify({
        url,
        goal: TINYFISH_GOAL,
        max_steps: 15,
        browser_profile: "stealth",
        proxy_config: { enabled: true, country_code: "US" },
      }),
    });
    if (!res.ok) return null;
    const runData = await res.json();
    const runId = runData.id || runData.run_id;
    if (!runId) return null;
    for (let attempt = 0; attempt < 60; attempt++) {
      await sleep(3000);
      const statusRes = await fetch(`https://agent.tinyfish.ai/v1/runs/${runId}`, {
        headers: { "X-API-Key": apiKey },
      });
      if (!statusRes.ok) continue;
      const statusData = await statusRes.json();
      const status = statusData.status;
      if (status === "COMPLETED") {
        const result = statusData.result;
        if (!result) return null;
        let text: string | undefined;
        if (typeof result === "string") text = result;
        else if (result.json) text = typeof result.json === "string" ? result.json : JSON.stringify(result.json);
        else if (result.response)
          text = typeof result.response === "string" ? result.response : JSON.stringify(result.response);
        else text = JSON.stringify(result);
        if (text && (text.trim().startsWith("{") || text.trim().startsWith("[")))
          return { text, status: 200 };
        return null;
      }
      if (status === "FAILED" || status === "CANCELLED") return null;
    }
    return null;
  } catch {
    return null;
  }
}

function fetchDirect(url: string): Promise<CruisersWikiFetchResult> {
  return fetch(url, { headers: HEADERS }).then(async (res) => ({
    text: await res.text(),
    status: res.status,
  }));
}

/**
 * Fetch Cruisers Wiki. Ordre: FlareSolverr → Proxy → extraFetcher (optionnel) → TinyFish → Direct.
 */
export async function cruisersWikiFetch(
  url: string,
  useTinyFish = false,
  options?: CruisersWikiFetchOptions
): Promise<CruisersWikiFetchResult> {
  const tryFetch = async (): Promise<CruisersWikiFetchResult> => {
    const fs = await fetchViaFlareSolverr(url);
    if (fs && isCruisersWikiValidJson(fs.text)) return fs;

    const px = await fetchViaProxy(url);
    if (px && px.status >= 200 && px.status < 400 && isCruisersWikiValidJson(px.text)) return px;

    if (options?.extraFetcher) {
      const extra = await options.extraFetcher(url);
      if (extra && extra.status >= 200 && extra.status < 400 && isCruisersWikiValidJson(extra.text)) return extra;
    }

    if (useTinyFish) {
      const tf = await fetchViaTinyFish(url);
      if (tf && isCruisersWikiValidJson(tf.text)) return tf;
    }

    return fetchDirect(url);
  };

  for (let attempt = 1; attempt <= RETRY_502; attempt++) {
    const result = await tryFetch();
    if (result.status >= 200 && result.status < 400 && isCruisersWikiValidJson(result.text)) return result;
    if (result.status !== 502 || attempt === RETRY_502) return result;
    await sleep(RETRY_DELAY_MS);
  }
  return tryFetch();
}
