"""Tests run with the stdlib only: python3 -m unittest discover -s tests -v"""
import pathlib
import shutil
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))

import sources  # noqa: E402
import warehouse  # noqa: E402


class TestParsing(unittest.TestCase):
    def test_salary_millions_range(self):
        self.assertEqual(warehouse.parse_salary_cop("$4 a $4,5 millones"), (4_000_000, 4_500_000))

    def test_salary_plain(self):
        self.assertEqual(warehouse.parse_salary_cop("$2.500.000"), (2_500_000, 2_500_000))

    def test_salary_confidential_is_null(self):
        self.assertEqual(warehouse.parse_salary_cop("Salario confidencial"), (None, None))

    def test_role_family(self):
        self.assertEqual(warehouse.family_of("Científico de datos junior"), "data_science")
        self.assertEqual(warehouse.family_of("Business intelligence junior"), "bi_analytics")
        self.assertEqual(warehouse.family_of("Business analyst de producto"), "business_analysis")
        self.assertEqual(warehouse.family_of("Ingeniero de datos IA y ML"), "data_engineering")


class TestPipeline(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self._db, self._exports = warehouse.DB, warehouse.EXPORTS
        warehouse.DB = self.tmp / "test.db"
        warehouse.EXPORTS = self.tmp / "exports"

    def tearDown(self):
        warehouse.DB, warehouse.EXPORTS = self._db, self._exports
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _run(self):
        offers = sources.scrape_all(offline=True)
        warehouse.load(offers, tracker_path=self.tmp / "no-tracker.json")
        return offers

    def test_load_creates_fact_rows(self):
        offers = self._run()
        con = __import__("sqlite3").connect(warehouse.DB)
        n = con.execute("SELECT COUNT(*) FROM fact_offer").fetchone()[0]
        con.close()
        self.assertEqual(n, len(offers))

    def test_idempotent_rerun(self):
        self._run()
        self._run()
        con = __import__("sqlite3").connect(warehouse.DB)
        n = con.execute("SELECT COUNT(*) FROM fact_offer").fetchone()[0]
        con.close()
        self.assertEqual(n, 10, "re-running must not duplicate rows")

    def test_marts_exist_and_export(self):
        self._run()
        written = dict(warehouse.export_marts())
        for mart in ("mart_market_by_family", "mart_funnel_by_country",
                     "mart_weekly_applications", "mart_salary_by_family", "mart_offer_sources"):
            self.assertIn(mart, written, f"{mart} missing")
        self.assertTrue((warehouse.EXPORTS / "fact_offer.csv").exists())

    def test_junior_flag(self):
        self._run()
        con = __import__("sqlite3").connect(warehouse.DB)
        rows = con.execute("SELECT title, is_junior FROM fact_offer").fetchall()
        con.close()
        flags = {t: j for t, j in rows}
        self.assertEqual(flags["Business intelligence junior"], 1)
        self.assertEqual(flags["Senior data scientist"], 0)


if __name__ == "__main__":
    unittest.main()
