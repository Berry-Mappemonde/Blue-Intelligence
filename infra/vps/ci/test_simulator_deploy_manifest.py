"""Le déploiement simulateur doit rsyncer film-front et ne pas effacer polar_data.

Ces contrôles visent l'arbre « simulateur » (infra/vps/naviguide/ +
naviguide-simulator/), absent de cette copie du dépôt : ici,
.github/workflows/deploy.yml ne déploie que Blue Intelligence et
infra/vps/ci/rsync-to-vps.sh n'implémente que le site `blue-intelligence`.
La classe est donc ignorée tant que cet arbre manque, et redevient active
dès qu'il est présent (dépôt jumeau / monorepo complet).
"""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

SIMULATOR_TREE = (
    ROOT / "infra" / "vps" / "naviguide",
    ROOT / "naviguide-simulator",
)
SIMULATOR_TREE_PRESENT = all(path.is_dir() for path in SIMULATOR_TREE)

SKIP_REASON = (
    "arbre simulateur absent de ce dépôt (infra/vps/naviguide/ + naviguide-simulator/) "
    "— déploiement Blue Intelligence uniquement, cf. .github/workflows/deploy.yml"
)


@unittest.skipUnless(SIMULATOR_TREE_PRESENT, SKIP_REASON)
class SimulatorDeployManifestTests(unittest.TestCase):
    def test_rsync_includes_film_front_unit(self):
        text = (ROOT / "infra/vps/ci/rsync-to-vps.sh").read_text(encoding="utf-8")
        self.assertIn("naviguide-film-front.service", text)

    def test_publish_mac_includes_film_front_unit(self):
        text = (ROOT / "infra/vps/naviguide/publish-simulator-from-mac.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn("naviguide-film-front.service", text)

    def test_rsync_excludes_polar_data_directory(self):
        text = (ROOT / "infra/vps/ci/rsync-to-vps.sh").read_text(encoding="utf-8")
        self.assertIn("--exclude server/polar_data/", text)

    def test_deploy_script_removes_zz_memory_dropin(self):
        text = (ROOT / "infra/vps/naviguide/deploy-simulator.sh").read_text(encoding="utf-8")
        self.assertIn("zz-memory.conf", text)

    def test_film_front_sources_present_in_repo(self):
        self.assertTrue(
            (ROOT / "infra/vps/naviguide/naviguide-film-front.service").is_file()
        )
        self.assertTrue((ROOT / "naviguide-simulator/server/film_front.py").is_file())


if __name__ == "__main__":
    unittest.main()
