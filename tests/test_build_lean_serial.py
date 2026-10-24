"""Check that the serial builder distinguishes stale targets from real errors."""

import unittest
from unittest.mock import patch

from tools.build_lean_serial import pending_targets, process_tree_usage


class PendingTargetsTests(unittest.TestCase):
    def test_lake_frontier(self):
        output = (
            "✖ [10/20] Running Example.First\n"
            "error: target is out-of-date and needs to be rebuilt\n"
            "✖ [11/20] Running Example.Second\n"
            "error: target is out-of-date and needs to be rebuilt\n"
            "Some required targets logged failures:\n"
            "- Example.First\n- Example.Second\n"
        )
        self.assertEqual(pending_targets(output), ["Example.First", "Example.Second"])

    def test_compilation_error_is_not_a_rebuild_request(self):
        output = (
            "error: unknown module prefix 'Missing'\n"
            "Some required targets logged failures:\n- Example.First\n"
        )
        with self.assertRaises(RuntimeError):
            pending_targets(output)

    def test_incomplete_diagnostic_stops(self):
        with self.assertRaises(RuntimeError):
            pending_targets("error: target is out-of-date and needs to be rebuilt\n")

    def test_memory_sample_excludes_other_sessions(self):
        listing = (
            "10 1 20 time\n11 10 100 lake\n12 11 1000 lean\n"
            "20 1 5000 lean\n"
        )
        with patch("subprocess.check_output", return_value=listing):
            self.assertEqual(process_tree_usage(10), (1120, 1000, 1))


if __name__ == "__main__":
    unittest.main()
