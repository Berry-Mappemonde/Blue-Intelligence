# VPS deploy CI

Used by `.github/workflows/deploy.yml`. Run on the GitHub runner
(`prepare-ssh.sh`, `rsync-to-vps.sh`) or on the VPS (`apply-site.sh`,
`apply-pending.sh`, `prod_jobs_busy.py`).

```bash
# On the VPS: is a Full / enrichment run in progress?
python3 infra/vps/ci/prod_jobs_busy.py --base-url http://127.0.0.1:8001
# 0 = idle, 10 = busy, 1 = probe failed
```

The probe sends a dedicated `User-Agent`: Cloudflare blocks `Python-urllib/3.x`.
A 404/410 endpoint is ignored (e.g. retired `generate-batch`).
The Review **Propose** batch (`GET /api/review/suggest/status`) requires
`ADMIN_KEY` (env or `backend/.env` on the VPS).
