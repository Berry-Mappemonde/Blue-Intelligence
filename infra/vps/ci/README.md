# CI de déploiement VPS

Utilisé par `.github/workflows/deploy.yml`. À lancer sur le runner GitHub
(`prepare-ssh.sh`, `rsync-to-vps.sh`) ou sur le VPS (`apply-site.sh`,
`apply-pending.sh`, `prod_jobs_busy.py`).

```bash
# Sur le VPS : y a-t-il un Complet / enrichissement en cours ?
python3 infra/vps/ci/prod_jobs_busy.py --base-url http://127.0.0.1:8001
# 0 = idle, 10 = occupé, 1 = sonde en échec
```
