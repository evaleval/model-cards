"""Build package data and the generation dependency from one tracked composer pin."""
import json
from pathlib import Path

from setuptools import setup
from setuptools.command.build_py import build_py

ROOT = Path(__file__).parent
PIN = json.loads((ROOT / "composer-pin.json").read_text(encoding="utf-8"))


class BuildPy(build_py):
    def run(self):
        super().run()
        target = Path(self.build_lib) / "model_cards/resources/composer-pin.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        self.copy_file(str(ROOT / "composer-pin.json"), str(target))

    def get_outputs(self, include_bytecode=1):
        return super().get_outputs(include_bytecode) + [
            str(Path(self.build_lib) / "model_cards/resources/composer-pin.json")
        ]


setup(
    cmdclass={"build_py": BuildPy},
    extras_require={
        "generate": [f"auto_benchmarkcard @ git+{PIN['repository_url']}@{PIN['commit']}"],
        "eval": ["anthropic>=0.40"],
    },
)
