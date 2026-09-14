import unittest

from corridor import bbox_around, first_sea_lonlat


class CorridorTest(unittest.TestCase):
    def test_la_rochelle_et_bbox(self):
        route = {
            "features": [
                {
                    "properties": {"name": "La Rochelle"},
                    "geometry": {"type": "Point", "coordinates": [-1.167, 46.1541]},
                }
            ]
        }
        lon, lat = first_sea_lonlat(route)
        self.assertAlmostEqual(lon, -1.167)
        self.assertAlmostEqual(lat, 46.1541)
        box = bbox_around(lon, lat, buffer_deg=0.5)
        self.assertEqual(len(box), 4)
        self.assertLess(box[0], lon)
        self.assertGreater(box[2], lon)


if __name__ == "__main__":
    unittest.main()
