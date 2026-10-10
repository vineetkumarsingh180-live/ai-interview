"""Runs the boundary checker on the real tree, and proves it detects violations."""
import os
import shutil
import subprocess
import sys

BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SCRIPT = os.path.join(BACKEND, "scripts", "check_architecture.py")


def run(root):
    return subprocess.run([sys.executable, SCRIPT, "--root", root], capture_output=True, text=True)


def test_repository_respects_module_boundaries():
    res = run(BACKEND)
    assert res.returncode == 0, res.stderr


def _copy(tmp_path):
    root = tmp_path / "backend"
    shutil.copytree(os.path.join(BACKEND, "app"), root / "app", ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(os.path.join(BACKEND, "alembic"), root / "alembic", ignore=shutil.ignore_patterns("__pycache__"))
    return root


def test_detects_cross_module_import(tmp_path):
    root = _copy(tmp_path)
    (root / "app/modules/voice_defense/bad.py").write_text("from app.modules.leaderboard.service import LeaderboardService\n")
    res = run(str(root))
    assert res.returncode == 1 and "no-cross-module-import" in res.stderr


def test_detects_relative_cross_module_import(tmp_path):
    root = _copy(tmp_path)
    (root / "app/modules/voice_defense/bad.py").write_text("from ..code_verifier.models import CandidateRepo\n")
    res = run(str(root))
    assert res.returncode == 1 and "no-cross-module-import" in res.stderr


def test_detects_shared_importing_module(tmp_path):
    root = _copy(tmp_path)
    (root / "app/shared/bad.py").write_text("from app.modules import leaderboard\n")
    res = run(str(root))
    assert res.returncode == 1 and "shared-must-be-independent" in res.stderr


def test_detects_business_logic_in_shared(tmp_path):
    root = _copy(tmp_path)
    (root / "app/shared/bad.py").write_text("def compute_candidate_score(x):\n    return x\n")
    res = run(str(root))
    assert res.returncode == 1 and "no-business-logic-in-shared" in res.stderr


def test_detects_core_importing_module_internals(tmp_path):
    root = _copy(tmp_path)
    (root / "app/core/bad.py").write_text("from app.modules.leaderboard.service import LeaderboardService\n")
    res = run(str(root))
    assert res.returncode == 1 and "only-public-api" in res.stderr


def test_detects_cross_module_persistence(tmp_path):
    root = _copy(tmp_path)
    (root / "app/modules/voice_defense/bad.py").write_text('QUERY = "select * from candidate_repos"\n')
    res = run(str(root))
    assert res.returncode == 1 and "no-cross-module-persistence" in res.stderr


def test_detects_cycle(tmp_path):
    root = _copy(tmp_path)
    (root / "app/modules/leaderboard/a.py").write_text("from . import b\n")
    (root / "app/modules/leaderboard/b.py").write_text("from . import a\n")
    res = run(str(root))
    assert res.returncode == 1 and "no-circular-imports" in res.stderr
