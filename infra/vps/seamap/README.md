# Self-hosted sea-chart mirror (Open Waters: Seamap)

Blue Intelligence's “Sea chart” basemap consumes the community
`tiles.openwaters.io` service by default — with no availability guarantee. This
folder installs a **mirror on the OVH VPS**: the dated PMTiles archive
(~26 GB), the style and the sprites are served by nginx from
`https://blueintelligence.online/tiles/seamap/`.

Licences: tiles/style/sprites **CC-BY 4.0** (“© Open Waters: Seamap”) on
**© OpenStreetMap contributors (ODbL)** data — the mirror keeps these
attributions (already shown by the frontend). No GPL code from the seamap
repository is used.

Disk budget: ~26 GB per archive, 2 archives kept (`KEEP=2`) →
**plan for ~55 GB free** on the VPS's 75 GB. If that is tight, set
`KEEP=1` (~30 GB).

## Installation (once)

From Terminal on your Mac, connect to the VPS:

```bash
ssh ubuntu@vps-52ba6d62.vps.ovh.net
```

Then, on the VPS:

```bash
# 1. Destination folder (immutable archive + nginx-served part)
sudo mkdir -p /srv/tiles/seamap/public
sudo chown -R ubuntu:ubuntu /srv/tiles

# 2. Sync script
cp ~/blue-intelligence-map/infra/vps/seamap/sync-seamap.sh /srv/tiles/seamap/
chmod +x /srv/tiles/seamap/sync-seamap.sh

# 3. Dry check: discover the upstream version (dated ETag)
/srv/tiles/seamap/sync-seamap.sh --check

# 4. Light test: style + sprites only (a few KB)
/srv/tiles/seamap/sync-seamap.sh --assets-only

# 5. Full sync (~26 GB — tens of minutes,
#    automatic resume if interrupted: rerun the same command)
/srv/tiles/seamap/sync-seamap.sh
```

### nginx

Open the site configuration:

```bash
sudo nano /etc/nginx/sites-available/blue-intelligence
```

In the HTTPS `server { … }` block (the one that contains `location / {`), add
the contents of `nginx-tiles.conf` (the `location /tiles/seamap/ { … }` block),
then:

```bash
sudo nginx -t && sudo systemctl reload nginx
curl -sI https://blueintelligence.online/tiles/seamap/style.json | head -5
```

> Cloudflare: the `current.pmtiles` file (~26 GB) is read in small
> byte ranges (`Range` headers), which Cloudflare lets through without
> caching. If you see slowness, create a “DNS only”
> (grey cloud) `tiles.blueintelligence.online` subdomain and use it in
> `PUBLIC_BASE_URL`.

### Weekly cron

```bash
sudo cp ~/blue-intelligence-map/infra/vps/seamap/seamap-sync.cron /etc/cron.d/seamap-sync
```

On Monday 06:30 UTC (upstream rebuilds its chart on Monday 03:00 UTC), the mirror
fetches the new dated archive, atomically switches `current.pmtiles` and
prunes archives beyond `KEEP`.

## Point the frontend at the mirror

`deploy-app.sh` detects the mirror automatically: if
`/srv/tiles/seamap/public/style.json` exists at build time, it writes
`REACT_APP_SEAMAP_STYLE_URL=https://blueintelligence.online/tiles/seamap/style.json`
into `frontend/.env`. Redeploy after the first
sync:

```bash
cd ~/blue-intelligence-map && bash infra/vps/deploy-app.sh
```

Without a mirror, the frontend keeps the public `tiles.openwaters.io` style — the
“Sea chart” mode works either way.

## What stays on origin CDNs

The mirror covers what seamap builds: the seamark layer (PMTiles), the
style and the nautical sprites. VersaTiles basemaps, Seascape bathymetry
and fonts stay on their CDNs (tens of GB, outside the VPS
budget). Accepted consequence: without a network path to those CDNs, the sea chart
shows marks on a neutral background.
