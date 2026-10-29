"""Tests for the ATS warehouse. They build the committed sample into a temp DB."""
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

try:
    import duckdb  # noqa: F401
    HAVE_DUCKDB = True
except ImportError:  # pragma: no cover - the base repo runs without it
    HAVE_DUCKDB = False

SAMPLE = ROOT / "data/sample/postings.parquet"


@unittest.skipUnless(HAVE_DUCKDB, "duckdb not installed (pip install -e '.[ats]')")
class TestAtsWarehouse(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from pipeline.ats import run
        cls.tmp = tempfile.TemporaryDirectory()
        cls.db = pathlib.Path(cls.tmp.name) / "test.duckdb"
        run(SAMPLE, cls.db)
        import duckdb
        cls.con = duckdb.connect(str(cls.db), read_only=True)

    @classmethod
    def tearDownClass(cls):
        cls.con.close()
        cls.tmp.cleanup()

    def one(self, sql):
        return self.con.execute(sql).fetchone()

    def test_fact_is_populated(self):
        n = self.one("select count(*) from fact_posting")[0]
        self.assertGreater(n, 4000, "sample should yield thousands of postings")

    def test_dedupe_never_increases_rows(self):
        landed, kept = self.one("select rows_landed, rows_after_dedupe from mart_quality")
        self.assertLessEqual(kept, landed)

    def test_every_fact_row_resolves_its_dimensions(self):
        orphans = self.one("""
            select count(*) from fact_posting
            where company_key is null or ats_key is null or role_key is null or location_key is null
        """)[0]
        self.assertEqual(orphans, 0)

    def test_ats_share_sums_to_100(self):
        total = self.one("select round(sum(pct), 0) from mart_ats_share")[0]
        self.assertAlmostEqual(float(total), 100.0, delta=1.0)

    def test_role_mix_sums_to_100(self):
        total = self.one("select round(sum(pct), 0) from mart_role_mix")[0]
        self.assertAlmostEqual(float(total), 100.0, delta=1.0)

    def test_no_null_country_label(self):
        nulls = self.one("select count(*) from dim_location where country is null")[0]
        self.assertEqual(nulls, 0, "unknown is a label, not a null")

    def test_body_and_date_stage_is_the_smallest(self):
        landed, kept, body_date = self.one("""
            select rows_landed, rows_after_dedupe,
                   (select count(*) from fact_posting where description_chars >= 200 and date_key is not null)
            from mart_quality""")
        self.assertLessEqual(body_date, kept)
        self.assertLessEqual(kept, landed)

    def test_dashboard_renders_from_the_warehouse(self):
        from dashboard.build_svg import build
        out = pathlib.Path(self.tmp.name) / "dashboard.svg"
        build(self.db, out)
        svg = out.read_text()
        self.assertTrue(svg.startswith("<svg"))
        self.assertIn("ATS", svg)
        self.assertGreater(len(svg), 5000)


if __name__ == "__main__":
    unittest.main()
