import unittest

from download_scenes import is_l2a_scene, product_name, require_l1c
from search_stac import DEFAULT_COLLECTION
from stamp import stamp_features


class HelpersTest(unittest.TestCase):
    def test_product_name_ajoute_safe(self):
        self.assertEqual(
            product_name("S2C_MSIL2A_20260912T110631_N0512_R137_T30TWR_20260912T145321"),
            "S2C_MSIL2A_20260912T110631_N0512_R137_T30TWR_20260912T145321.SAFE",
        )
        self.assertEqual(product_name("X.SAFE"), "X.SAFE")

    def test_recherche_par_defaut_l1c(self):
        self.assertEqual(DEFAULT_COLLECTION, "sentinel-2-l1c")

    def test_refuse_l2a_pour_acolite(self):
        self.assertTrue(is_l2a_scene(
            "S2C_MSIL2A_20260912T110631_N0512_R137_T30TWR_20260912T145321"
        ))
        self.assertFalse(is_l2a_scene(
            "S2C_MSIL1C_20260912T110631_N0512_R137_T30TWR_20260912T123456"
        ))
        with self.assertRaises(SystemExit) as ctx:
            require_l1c("S2C_MSIL2A_20260912T110631_N0512_R137_T30TWR_20260912T145321")
        self.assertIn("L2A", str(ctx.exception))

    def test_stamp_coastline(self):
        raw = {
            "type": "FeatureCollection",
            "features": [{
                "type": "Feature",
                "geometry": {"type": "LineString", "coordinates": [[-1.2, 46.1], [-1.1, 46.2]]},
                "properties": {},
            }],
        }
        out = stamp_features(raw, "sentinel-coastline")
        p = out["features"][0]["properties"]
        self.assertEqual(p["source"], "sentinel-pilot")
        self.assertEqual(p["natural"], "coastline")
        self.assertTrue(p["name"])


if __name__ == "__main__":
    unittest.main()
