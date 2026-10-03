"""dualsense/states.py: enumeration with impossible combinations removed, rule checking, grouping."""
import unittest

from dualsense import states as S


class Enumerate(unittest.TestCase):
    def test_expand_drops_impossible(self):
        out = S.expand({"a": [0, 1], "b": ["x", "y"]}, [lambda s: s["a"] == 0 and s["b"] == "y"])
        self.assertEqual(out, [{"a": 0, "b": "x"}, {"a": 1, "b": "x"}, {"a": 1, "b": "y"}])

    def test_violations_and_summary(self):
        rows = [{"state": {"a": 0}, "out": {"rt": "NORMAL"}}, {"state": {"a": 1}, "out": {"rt": "NORMAL"}}]
        self.assertEqual(S.violations(rows, [("a is 0", lambda s, o: s["a"] == 0)]), [("a=1", "a is 0")])
        self.assertTrue(S.summary(rows).startswith("2 states, 1 different controller outputs"))


if __name__ == "__main__":
    unittest.main()
