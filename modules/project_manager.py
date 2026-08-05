"""Package entry point for the project manager."""

import importlib
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

_module = importlib.import_module("project_manager")
globals().update({name: getattr(_module, name) for name in dir(_module) if not name.startswith("__")})
__all__ = [name for name in dir(_module) if not name.startswith("__")]
