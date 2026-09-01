from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]


class SkillMetadataTests(unittest.TestCase):
    def test_all_four_skills_have_valid_frontmatter(self):
        files = sorted((ROOT / "skills").glob("*/SKILL.md"))
        self.assertEqual(len(files), 4)
        for path in files:
            content = path.read_text(encoding="utf-8")
            self.assertTrue(content.startswith("---\n"), path)
            end = content.find("\n---\n", 4)
            self.assertGreater(end, 0, path)
            frontmatter = content[4:end]
            name_match = re.search(r"^name:\s*(.+)$", frontmatter, re.MULTILINE)
            description_match = re.search(r"^description:\s*(.+)$", frontmatter, re.MULTILINE)
            self.assertIsNotNone(name_match, path)
            self.assertIsNotNone(description_match, path)
            name = name_match.group(1).strip()
            description = description_match.group(1).strip()
            self.assertRegex(name, r"^[a-z0-9-]{1,64}$")
            self.assertLessEqual(len(description), 1024)
            self.assertTrue(content[end + 5:].strip())
            self.assertLessEqual(len(content), 100_000)


if __name__ == "__main__":
    unittest.main()
