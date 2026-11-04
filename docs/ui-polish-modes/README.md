# Mode sidebar polish

Merge after [#52](https://github.com/Berry-Mappemonde/Blue-Intelligence/pull/52). Target: `feat/integrate-poe-pipeline`.

Projects first, then Marinas, Offices, MPA, Science and Climo. This change reuses #52's `m-*` tokens, Inter typography, fields, secondary buttons, disclosure legends and numeric text roles. Category colours retain their meaning. Sidebar surfaces, hover states, text, borders and scrollbars use the existing neutral tokens. There are no new dependencies or token definitions.

Only the seven sidebar/list components and their EN/FR presentation copy change. Component non-render logic, filters, handlers, API calls, polling and data contracts are unchanged. The protected top nav, global CSS/tokens, App, PoE components, map/polygon styling, Console and Review have no changes relative to the parent `ui-polish` branch.

## Visual evidence

Each image is a 1440 × 1000 CSS-pixel viewport at device scale 1. Before images use the original `ui-polish` sidebar source at `fbc44c7`; the subsequent #52 commits do not change these sidebars. After images show this branch rebased onto #52 at `ad8d162`. Both use the isolated clone's frontend on 3004 and backend on 8004, with the navigation notice acknowledged through its controls.

Projects contains 4,463 live records. The configured backend returns zero marinas, so that pair shows the real empty state. No fixture data appears in these four PR images. The existing map and top nav are outside this change.

| Mode | Before | After |
| --- | --- | --- |
| Projects | [Before](before-projects.jpg) | [After](after-projects.jpg) |
| Marinas | [Before](before-marinas.jpg) | [After](after-marinas.jpg) |

## Validation

- `CI=true npm test -- --runInBand`: 13 suites, 67 tests pass.
- `CI=true npm run build`: compiled successfully.
- Headless Chrome: all six sidebars in EN and FR at 1440 × 1000, 1280 × 720 and 390 × 844; no sidebar horizontal overflow and Inter applied.
- Keyboard disclosure open/close, search including no matches, Projects organisation/category filters, Science source filters, MPA LFP filters, Climo month keyboard input, swell statistics and point details checked.
- Browser-only fixtures exercise populated Marinas, Offices, MPA and Science rows, long names, missing names and Climo values without backend writes. The required before/after images use real backend responses.
- No uncaught browser errors during the interaction checks.
- Parsed component comparison confirms non-render logic is unchanged. `git diff --check` passes.

The existing top nav crowds at 390px. It is outside the authorised scope; the sidebar itself fits and scrolls independently.

## Local preview

Clone: `/private/tmp/blue-intelligence-modes`. Backend: `http://localhost:8004`; frontend: `http://localhost:3004`. The ignored backend `.env` was copied from the requested v2 checkout without printing its contents. `CORS_ORIGINS=http://localhost:3004` is set only in the backend process environment. Uvicorn runs with `--lifespan off` so preview startup does not drop legacy collections or resume background jobs.

The frontend uses `REACT_APP_BACKEND_URL=http://localhost:8004` and `PORT=3004`. CRA's hard-coded npm start port is bypassed by invoking its start script directly. A process-local configuration wrapper supplies `allowedHosts: ["localhost", "127.0.0.1"]` to work around CRA's undefined LAN host with an explicit loopback bind. Repository configuration is unchanged. Ports 8002/3002 are untouched.
