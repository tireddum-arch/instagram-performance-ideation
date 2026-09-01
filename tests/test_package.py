from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
WIKI_SCRIPT = ROOT / "skills" / "meme-llm-wiki" / "scripts" / "meme_wiki.py"
INSTALL_SCRIPT = ROOT / "install.py"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


WIKI = load_module("meme_wiki", WIKI_SCRIPT)
INSTALLER = load_module("package_installer", INSTALL_SCRIPT)


class MemeWikiTests(unittest.TestCase):
    def test_initialize_is_non_destructive(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "meme-wiki"
            created = WIKI.initialize(root)
            self.assertTrue(created)
            audience = root / "brand" / "audience.md"
            audience.write_text("custom audience", encoding="utf-8")
            WIKI.initialize(root)
            self.assertEqual(audience.read_text(encoding="utf-8"), "custom audience")

    def test_approved_entry_updates_raw_format_and_context(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "meme-wiki"
            proposal = Path(directory) / "proposal.json"
            proposal.write_text(json.dumps({
                "text": "exact source text",
                "side_text": "tiny aside",
                "structure": "[serious setup] then [low-energy admission]",
                "format_slug": "serious-drop",
                "format_title": "Serious setup drop",
                "why_it_works": "the reader recognizes the sudden loss of energy",
                "application": "replace the situation while keeping the status drop",
            }), encoding="utf-8")
            result = WIKI.add_entry(root, proposal, "test", "", None)
            raw = json.loads((root / "raw" / "memes.json").read_text())
            self.assertEqual(raw[0]["id"], result["id"])
            format_text = (root / "formats" / "serious-drop.md").read_text()
            self.assertIn("exact source text", format_text)
            self.assertIn("serious-drop", str(result["format"]))
            self.assertIn("Serious setup drop", WIKI.context(root))

    def test_validation_rejects_unsafe_slug(self):
        entry = {field: "value" for field in WIKI.REQUIRED}
        entry["format_slug"] = "../../escape"
        with self.assertRaises(ValueError):
            WIKI.validate_entry(entry)


class InstallerTests(unittest.TestCase):
    def test_installer_copies_all_four_skills(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "installed"
            installed = INSTALLER.install(ROOT, destination, force=False)
            self.assertEqual(
                {path.name for path in installed},
                {"instagram-performance-ideation", "meme-collector", "meme-llm-wiki", "meme-writer"},
            )
            for path in installed:
                self.assertTrue((path / "SKILL.md").is_file())


if __name__ == "__main__":
    unittest.main()
