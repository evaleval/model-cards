from __future__ import annotations

from importlib.resources import files
import os
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
import zipfile


class PackagingTests(unittest.TestCase):
    ROOT = Path(__file__).resolve().parents[1]

    def _build_wheel(self, root: Path) -> Path:
        checkout = root / "checkout"
        shutil.copytree(
            self.ROOT,
            checkout,
            ignore=shutil.ignore_patterns(".git", ".venv", "build", "dist", "*.egg-info"),
        )
        destination = root / "dist"
        result = subprocess.run(
            (
                "/usr/bin/python3",
                "setup.py",
                "bdist_wheel",
                "--dist-dir",
                str(destination),
            ),
            cwd=checkout,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        wheels = list(destination.glob("*.whl"))
        self.assertEqual(len(wheels), 1)
        return wheels[0]

    def test_installed_package_exposes_the_schema_resource(self) -> None:
        resource = files("model_cards").joinpath("resources", "model-card.schema.json")
        self.assertIn('"$schema": "https://json-schema.org/draft/2020-12/schema"', resource.read_text())

    def test_built_wheel_contains_the_contract_and_no_sibling_imports(self) -> None:
        with TemporaryDirectory() as temporary:
            wheel = self._build_wheel(Path(temporary))
            with zipfile.ZipFile(wheel) as archive:
                names = set(archive.namelist())
                metadata_name = next(name for name in names if name.endswith(".dist-info/METADATA"))
                metadata = archive.read(metadata_name).decode("utf-8")
            self.assertIn("model_cards/resources/model-card.schema.json", names)
            self.assertIn("model_cards/resources/audit-card.schema.json", names)
            self.assertIn("model_cards/contract.py", names)
            self.assertIn("model_cards/publication_schema.py", names)
            self.assertIn("Requires-Dist: jsonschema", metadata)
            self.assertIn("Provides-Extra: risk", metadata)
            self.assertIn("ai-atlas-nexus", metadata)
            self.assertFalse(any("model-card-system" in name for name in names))
            self.assertFalse(any("auto_benchmarkcard" in name for name in names))

            entry_points_name = next(
                name for name in names if name.endswith(".dist-info/entry_points.txt")
            )
            with zipfile.ZipFile(wheel) as archive:
                entry_points = archive.read(entry_points_name).decode("utf-8")
            self.assertIn("model-cards = model_cards.cli:main", entry_points)
            self.assertIn("modelcards = model_cards.cli:main", entry_points)

    @unittest.skipUnless(
        os.environ.get("MODEL_CARDS_RUN_CLEAN_INSTALL") == "1",
        "set MODEL_CARDS_RUN_CLEAN_INSTALL=1 for networked clean-install acceptance",
    )
    def test_clean_venv_installs_and_validates_without_adjacent_repositories(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            wheel = self._build_wheel(root)
            environment = root / "clean-venv"
            create = subprocess.run(
                ("/usr/bin/python3", "-m", "venv", str(environment)),
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(create.returncode, 0, create.stdout + create.stderr)
            python = environment / "bin" / "python"
            install = subprocess.run(
                (str(python), "-m", "pip", "install", str(wheel)),
                cwd=root,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(install.returncode, 0, install.stdout + install.stderr)
            probe = subprocess.run(
                (
                    str(python),
                    "-I",
                    "-c",
                    (
                        "from model_cards.publication_schema import blank_publication_card, "
                        "load_publication_schema, validate_publication_card; "
                        "from model_cards.cli import main; "
                        "assert len(load_publication_schema()['properties'])==7; "
                        "card=blank_publication_card(); "
                        "card['identity']['model_id']='example/model'; "
                        "card['identity']['version']='a'*40; "
                        "validate_publication_card(card); "
                        "assert main(['schema']) == 0"
                    ),
                ),
                cwd=root,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(probe.returncode, 0, probe.stdout + probe.stderr)


if __name__ == "__main__":
    unittest.main()
