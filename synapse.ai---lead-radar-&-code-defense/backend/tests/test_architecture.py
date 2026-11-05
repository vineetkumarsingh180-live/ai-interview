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


# ---- AIService boundary rules: each violation is injected into a copy of the real project --------
AISERVICE = os.path.abspath(os.path.join(BACKEND, "..", "AIService"))
DBINGESTION = os.path.abspath(os.path.join(BACKEND, "..", "DbIngestion"))


def _project(tmp_path):
    """tmp/backend + tmp/AIService + tmp/DbIngestion, so the checker finds its siblings."""
    ig = shutil.ignore_patterns("__pycache__", "*.egg-info", "tests", ".pytest_cache")
    backend = tmp_path / "backend"
    shutil.copytree(os.path.join(BACKEND, "app"), backend / "app", ignore=ig)
    shutil.copytree(os.path.join(BACKEND, "alembic"), backend / "alembic", ignore=ig)
    shutil.copytree(os.path.join(AISERVICE, "aiservice"), tmp_path / "AIService" / "aiservice", ignore=ig)
    shutil.copytree(os.path.join(DBINGESTION, "dbingestion"), tmp_path / "DbIngestion" / "dbingestion", ignore=ig)
    return backend


def _expect(tmp_path, rule, relpath, source):
    backend = _project(tmp_path)
    target = backend.parent / relpath
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(source)
    res = run(str(backend))
    assert res.returncode == 1 and rule in res.stderr, (rule, res.stdout, res.stderr)


def test_clean_copy_of_the_project_passes(tmp_path):
    res = run(str(_project(tmp_path)))
    assert res.returncode == 0, res.stderr


def test_detects_module_importing_aiservice(tmp_path):
    _expect(tmp_path, "aiservice-only-via-composition-root", "backend/app/modules/job_lead_radar/bad.py",
            "from aiservice import LeadIntelligence\n")


def test_detects_shared_code_importing_aiservice_outside_ai_py(tmp_path):
    _expect(tmp_path, "aiservice-only-via-composition-root", "backend/app/shared/bad.py", "import aiservice\n")


def test_detects_ingestion_importing_aiservice(tmp_path):
    _expect(tmp_path, "ingestion-must-not-import-aiservice", "DbIngestion/dbingestion/bad.py", "from aiservice import GeminiProvider\n")


def test_detects_aiservice_importing_fastapi(tmp_path):
    _expect(tmp_path, "aiservice-framework-independent", "AIService/aiservice/bad.py", "from fastapi import APIRouter\n")


def test_detects_aiservice_importing_the_orm(tmp_path):
    _expect(tmp_path, "aiservice-framework-independent", "AIService/aiservice/bad.py", "import sqlalchemy\n")


def test_detects_aiservice_importing_backend_modules(tmp_path):
    _expect(tmp_path, "aiservice-framework-independent", "AIService/aiservice/lead_intelligence/bad.py",
            "from app.modules.job_lead_radar.models import JobLead\n")


def test_detects_aiservice_running_code(tmp_path):
    _expect(tmp_path, "aiservice-no-code-execution", "AIService/aiservice/bad.py", "import subprocess\nsubprocess.run(['ls'])\n")


def test_detects_aiservice_import_cycle(tmp_path):
    backend = _project(tmp_path)
    pkg = backend.parent / "AIService" / "aiservice" / "shared"
    (pkg / "cyc_a.py").write_text("from . import cyc_b\n")
    (pkg / "cyc_b.py").write_text("from . import cyc_a\n")
    res = run(str(backend))
    assert res.returncode == 1 and "aiservice-no-circular-imports" in res.stderr


def test_detects_provider_sdk_outside_providers(tmp_path):
    _expect(tmp_path, "provider-sdk-centralized", "AIService/aiservice/lead_intelligence/bad.py", "import openai\n")


def test_detects_hardcoded_gemini_url_in_the_backend(tmp_path):
    _expect(tmp_path, "provider-sdk-centralized", "backend/app/modules/voice_defense/bad.py",
            'URL = "https://generativelanguage.googleapis.com/v1beta/models"\n')


def test_detects_gemini_key_read_outside_config(tmp_path):
    _expect(tmp_path, "gemini-key-centralized", "backend/app/modules/voice_defense/bad.py",
            "from app.shared.config import settings\nKEY = settings.GEMINI_API_KEY\n")


def test_detects_a_second_api_server(tmp_path):
    _expect(tmp_path, "single-api-server", "AIService/aiservice/bad.py", "from x import FastAPI\napp = FastAPI()\n")


def test_detects_a_node_backend(tmp_path):
    _expect(tmp_path, "no-node-backend", "frontend/package.json", '{"dependencies": {"express": "^4.0.0"}}')
    shutil.rmtree(tmp_path / "frontend")
    _expect(tmp_path / "second", "no-node-backend", "server.ts", "import express from 'express';\n")
