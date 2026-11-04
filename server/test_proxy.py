"""The proxy is the only door to both services: a path it forgets is a feature that silently never works."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import proxy  # noqa: E402


class TargetForTest(unittest.TestCase):
    def test_search_and_categories_go_to_the_search_service(self):
        for path in ("/search?q=klcc", "/categories", "/search?category=fuel&lat=3&lon=101"):
            self.assertIs(proxy.target_for(path), proxy.SEARCH_SRV, path)

    def test_everything_else_goes_to_valhalla(self):
        for path in ("/status", "/route", "/locate", "/isochrone"):
            self.assertIs(proxy.target_for(path), proxy.VALHALLA_SRV, path)

    def test_a_lookalike_path_is_not_mistaken_for_search(self):
        self.assertIs(proxy.target_for("/searchish"), proxy.SEARCH_SRV)  # prefix match, by design
        self.assertIs(proxy.target_for("/Search"), proxy.VALHALLA_SRV)   # case matters, as in HTTP


if __name__ == "__main__":
    unittest.main()
