import unittest

from tests.source_scan import Source


class ReadingImports(unittest.TestCase):
    def test_a_from_import_of_the_whole_package_names_each_ring(self):
        self.assertEqual(Source("from chronata import adapters, wiring\n").chronata_imports(), [(1, "chronata.adapters"), (1, "chronata.wiring")])

    def test_a_bare_import_of_the_whole_package_is_seen(self):
        self.assertEqual(Source("import chronata\n").chronata_imports(), [(1, "chronata")])

    def test_imports_from_elsewhere_are_not_chronata_imports(self):
        self.assertEqual(Source("import json\nfrom chronatable import x\n").chronata_imports(), [])

    def test_a_relative_import_is_seen(self):
        self.assertTrue(Source("from .day import Day\n").has_relative_import())

    def test_an_absolute_import_is_not_relative(self):
        self.assertFalse(Source("from chronata.timekeeping.hours.day import Day\n").has_relative_import())


class ReadingWhatCodeUses(unittest.TestCase):
    def test_a_built_in_passed_along_without_being_called_is_seen(self):
        self.assertIn("open", Source("def load(path, reader=open):\n    return reader(path)\n").names_used())

    def test_a_module_reached_through_another_is_seen(self):
        self.assertIn("sys", Source("import dataclasses\ndataclasses.sys.modules\n").attributes_used())


    def test_a_module_brought_in_with_a_from_import_is_seen(self):
        self.assertEqual(Source("from json import codecs\n").names_imported_from(), [("json", "codecs")])

    def test_what_is_reached_through_an_imported_module_is_seen(self):
        source = Source("import json as j\nj.codecs.open\n")
        self.assertEqual((source.modules_bound(), source.attributes_of("j")), ({"j": "json"}, ["codecs"]))


if __name__ == "__main__":
    unittest.main()
