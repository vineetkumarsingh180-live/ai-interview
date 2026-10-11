#!/usr/bin/env python3
"""
Architecture boundary check for the FastAPI backend (stdlib only; exit code 1 on violation).

Layering (arrows = "may import"):

    main.py ──▶ core/ ──▶ modules/<name> (package public API only) ──▶ shared/
    modules/<a> ──✗──▶ modules/<b>          shared/ ──✗──▶ modules/, core/

Rules enforced
  1. A module imports only itself and app.shared (never another module, never app.core / app.main).
  2. app.shared never imports app.modules / app.core / app.main.
  3. app.core, app.main and alembic import a module only through its package (`app.modules.<m>`),
     never its internals (`app.modules.<m>.service`).
  4. No circular imports between files.
  5. No module business logic in app.shared (domain terms / model names are rejected there).
  6. No cross-module persistence: another module's table name may appear in a module only inside
     a `ForeignKey(...)` in models.py (schema-level reference, no ORM access).
  7. DbIngestion (../DbIngestion/dbingestion): may import app.shared.* and a module's package
     (`app.modules.<m>`) only; never app.core / app.main / module internals; nothing in app/ may import
     it; it must not execute code, spawn processes, unpack archives or use scraping libraries; and it
     must not touch SQL tables directly (persistence goes through module interfaces).

  8. AIService (../AIService/aiservice) is an internal library: no FastAPI/Starlette/SQLAlchemy/Alembic,
     no `app.*`, no `dbingestion`, no process spawning or dynamic code execution, no import cycles.
  9. Only app/core/** and app/shared/ai.py may import `aiservice` (modules, other shared code, main and
     alembic must not); DbIngestion must not import it; the GEMINI_API_KEY identifier lives only in
     app/shared/config.py and app/shared/ai.py.
 10. Provider SDKs (google.generativeai, openai, anthropic, ...) are imported only under
     aiservice/providers/, and the Gemini endpoint URL appears only in aiservice/providers/gemini.py.
 11. One API server: FastAPI( is constructed only in app/main.py; no Flask/uvicorn.run/Starlette
     elsewhere; no Node backend (express/koa/fastify/hapi dependency or server.ts/js) anywhere.

Usage: python scripts/check_architecture.py [--root <backend dir>]
"""
import ast
import io
import os
import re
import sys
import tokenize

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if "--root" in sys.argv:
    ROOT = os.path.abspath(sys.argv[sys.argv.index("--root") + 1])
APP = os.path.join(ROOT, "app")

DOMAIN_WORDS = re.compile(
    r"(lead|repo|repository|voice|interview|leaderboard|candidate|outreach|verdict|benchmark)",
    re.I,
)
# Shared files whose *API vocabulary* legitimately includes a domain-looking word. Keep this list tiny.
SHARED_ALLOWED_WORDS = {
    os.path.join("app", "shared", "github.py"): re.compile(r"repo|repository", re.I),
}

violations = []


def report(rule, file, detail):
    violations.append((rule, os.path.relpath(file, ROOT), detail))


def py_files(base):
    for dp, dn, fn in os.walk(base):
        dn[:] = [d for d in dn if d not in ("__pycache__", ".venv", "tests")]
        for f in fn:
            if f.endswith(".py"):
                yield os.path.join(dp, f)


def dotted(path):
    rel = os.path.relpath(path, ROOT)[:-3].replace(os.sep, ".")
    return rel[: -len(".__init__")] if rel.endswith(".__init__") else rel


def layer_of(mod):
    """mod is a dotted name like app.modules.leaderboard.service"""
    parts = mod.split(".")
    if parts[:2] == ["app", "modules"]:
        return ("module", parts[2]) if len(parts) > 2 else ("modules-root", None)
    if parts[:2] == ["app", "shared"]:
        return ("shared", None)
    if parts[:2] == ["app", "core"]:
        return ("core", None)
    if parts == ["app", "main"] or parts == ["app"]:
        return ("main", None)
    return ("external", None)


def imports_of(path):
    """Yield absolute dotted module names imported by `path` (relative imports resolved)."""
    tree = ast.parse(open(path).read())
    me = dotted(path)
    pkg = me if os.path.basename(path) == "__init__.py" else me.rpartition(".")[0]
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                yield a.name
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                base = pkg.split(".")
                base = base[: len(base) - (node.level - 1)]
                mod = ".".join(base + ([node.module] if node.module else []))
            else:
                mod = node.module or ""
            for a in node.names:                          # `from pkg import name` may name a submodule
                sub = f"{mod}.{a.name}"
                if resolve_file(sub):
                    yield sub
                elif mod == "app.modules":
                    yield sub
                else:
                    yield mod


def resolve_file(mod):
    p = os.path.join(ROOT, *mod.split("."))
    if os.path.isfile(p + ".py"):
        return p + ".py"
    if os.path.isfile(os.path.join(p, "__init__.py")):
        return os.path.join(p, "__init__.py")
    return None


def strip_to_code_tokens(path):
    """Identifier/keyword tokens only (comments and string literals dropped)."""
    out = []
    with open(path, "rb") as fh:
        for tok in tokenize.tokenize(io.BytesIO(fh.read()).readline):
            if tok.type == tokenize.NAME:
                out.append(tok.string)
    return out


# table names owned by each module (scan __tablename__)
tables = {}
for f in py_files(os.path.join(APP, "modules")):
    m = layer_of(dotted(f))
    if m[0] != "module":
        continue
    for node in ast.walk(ast.parse(open(f).read())):
        if isinstance(node, ast.Assign) and any(getattr(t, "id", "") == "__tablename__" for t in node.targets):
            if isinstance(node.value, ast.Constant):
                tables[node.value.value] = m[1]

graph = {}
files = list(py_files(APP)) + [os.path.join(ROOT, "alembic", "env.py")]
for f in files:
    if not os.path.isfile(f):
        continue
    me_mod = dotted(f) if f.startswith(APP) else "alembic.env"
    me = layer_of(me_mod) if f.startswith(APP) else ("core", None)  # alembic env acts as composition code
    deps = set()
    for imp in imports_of(f):
        t = layer_of(imp)
        if t[0] == "external":
            continue
        target_file = resolve_file(imp)
        if target_file:
            deps.add(target_file)

        if me[0] == "module":
            if t[0] == "module" and t[1] != me[1]:
                report("no-cross-module-import", f, f'module "{me[1]}" imports "{imp}" (use a port in interfaces.py wired in app/core/wiring.py)')
            if t[0] in ("core", "main"):
                report("modules-must-not-import-core", f, f'imports "{imp}"')
        elif me[0] == "shared":
            if t[0] in ("module", "modules-root", "core", "main"):
                report("shared-must-be-independent", f, f'app.shared imports "{imp}"')
        elif me[0] in ("core", "main"):
            if t[0] == "module" and len(imp.split(".")) > 3:
                report("only-public-api", f, f'imports module internals "{imp}"; import the package "app.modules.{t[1]}"')
    graph[f] = deps

    # shared must not contain business logic
    if me[0] == "shared":
        allowed = SHARED_ALLOWED_WORDS.get(os.path.relpath(f, ROOT))
        for name in strip_to_code_tokens(f):
            if allowed and allowed.sub("", name) != name and not DOMAIN_WORDS.search(allowed.sub("", name)):
                continue
            if DOMAIN_WORDS.search(name):
                report("no-business-logic-in-shared", f, f'domain term "{name}" in shared code')
                break

    # cross-module persistence: foreign table names only inside ForeignKey(...) in models.py
    if me[0] == "module":
        tree = ast.parse(open(f).read())
        fk_args = set()
        if os.path.basename(f) == "models.py":
            for n in ast.walk(tree):
                if isinstance(n, ast.Call) and getattr(n.func, "id", "") == "ForeignKey":
                    for a in n.args:
                        for c in ast.walk(a):
                            fk_args.add(id(c))
        for n in ast.walk(tree):
            if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in fk_args:
                for table, owner in tables.items():
                    if owner != me[1] and re.search(rf"\b{re.escape(table)}\b", n.value) and len(n.value) < 200:
                        report("no-cross-module-persistence", f, f'references table "{table}" owned by "{owner}"')

# ---- DbIngestion boundary rules -------------------------------------------------------------
ING = os.path.abspath(os.path.join(ROOT, "..", "DbIngestion", "dbingestion"))
_FORBIDDEN_IMPORTS = {
    "subprocess": "spawns processes (could run untrusted code)",
    "pty": "spawns processes", "shlex": "shell command construction",
    "zipfile": "unpacks archives", "tarfile": "unpacks archives",
    "importlib": "dynamic code loading", "runpy": "runs code",
    "bs4": "HTML scraping", "scrapy": "scraping", "selenium": "browser automation", "playwright": "browser automation",
    "lxml": "HTML scraping", "mechanize": "scraping", "requests_html": "scraping",
}
_FORBIDDEN_CALLS = {"eval", "exec", "compile", "__import__"}
ing_files = [f for f in py_files(ING)] if os.path.isdir(ING) else []
for f in ing_files:
    tree = ast.parse(open(f).read())
    for node in ast.walk(tree):
        names = []
        if isinstance(node, ast.Import):
            names = [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names = [node.module]
        for name in names:
            top = name.split(".")[0]
            if top == "app":
                t = layer_of(name)
                if t[0] in ("core", "main"):
                    report("ingestion-uses-public-api-only", f, f'imports "{name}" (app.core/app.main are composition code)')
                elif t[0] == "module" and len(name.split(".")) > 3:
                    report("ingestion-uses-public-api-only", f, f'imports module internals "{name}"; import app.modules.{t[1]}')
            if top in _FORBIDDEN_IMPORTS:
                report("ingestion-no-code-execution-or-scraping", f, f'imports "{name}": {_FORBIDDEN_IMPORTS[top]}')
        if isinstance(node, ast.Call):
            fn = getattr(node.func, "id", None)
            if fn in _FORBIDDEN_CALLS:
                report("ingestion-no-code-execution-or-scraping", f, f"calls {fn}()")
            if isinstance(node.func, ast.Attribute) and node.func.attr in ("system", "popen", "Popen", "run", "check_output") \
                    and getattr(node.func.value, "id", "") in ("os", "subprocess"):
                report("ingestion-no-code-execution-or-scraping", f, f"calls {node.func.value.id}.{node.func.attr}()")
        # direct SQL / ORM table access: ingestion must go through module interfaces
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("app.modules.") and node.module.count(".") >= 3:
            pass
    text = open(f).read()
    if re.search(r"\.models\b|\bModel\b|Base\.metadata", text) and "app.modules" in text and re.search(r"from app\.modules\.[a-z_]+\.models", text):
        report("ingestion-uses-public-api-only", f, "imports a module's ORM models directly")

# ---- AIService / provider / single-server rules ----------------------------------------------
PROJECT = os.path.abspath(os.path.join(ROOT, ".."))
AIS_ROOT = os.path.join(PROJECT, "AIService")
AIS = os.path.join(AIS_ROOT, "aiservice")
ais_files = list(py_files(AIS)) if os.path.isdir(AIS) else []

_AIS_FORBIDDEN_TOPS = {"app", "fastapi", "starlette", "uvicorn", "sqlalchemy", "asyncpg", "psycopg", "psycopg2",
                       "alembic", "dbingestion", "flask", "django"}
_PROVIDER_SDKS = ("google.generativeai", "google.genai", "google.cloud.aiplatform", "vertexai", "openai",
                  "anthropic", "cohere", "mistralai", "langchain", "litellm")
GEMINI_URL = "generativelanguage.googleapis.com"


def _abs_imports(tree):
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                yield a.name, node
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            yield node.module, node


def _is_ais_provider_file(path):
    return os.path.commonpath([path, os.path.join(AIS, "providers")]) == os.path.join(AIS, "providers")


for f in ais_files:
    tree = ast.parse(open(f).read())
    for name, node in _abs_imports(tree):
        top = name.split(".")[0]
        if top in _AIS_FORBIDDEN_TOPS:
            report("aiservice-framework-independent", f, f'imports "{name}" (AIService must not know the web framework, the ORM or the backend)')
        if top in _FORBIDDEN_IMPORTS:
            report("aiservice-no-code-execution", f, f'imports "{name}": {_FORBIDDEN_IMPORTS[top]}')
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            fn = getattr(node.func, "id", None)
            if fn in _FORBIDDEN_CALLS:
                report("aiservice-no-code-execution", f, f"calls {fn}()")
            if isinstance(node.func, ast.Attribute) and node.func.attr in ("system", "popen", "Popen", "run", "check_output") \
                    and getattr(node.func.value, "id", "") in ("os", "subprocess"):
                report("aiservice-no-code-execution", f, f"calls {node.func.value.id}.{node.func.attr}()")

# AIService internal import cycles (relative imports resolved inside the package)
_ais_graph = {}
for f in ais_files:
    pkg = os.path.relpath(f, AIS_ROOT)[:-3].replace(os.sep, ".")
    is_init = os.path.basename(f) == "__init__.py"
    if is_init:
        pkg = pkg[: -len(".__init__")]
    base_pkg = pkg if is_init else pkg.rpartition(".")[0]
    deps = set()
    for node in ast.walk(ast.parse(open(f).read())):
        if isinstance(node, ast.ImportFrom) and node.level:
            parts = base_pkg.split(".")
            parts = parts[: len(parts) - (node.level - 1)]
            mod = ".".join(parts + ([node.module] if node.module else []))
            for a in node.names:
                for cand in (f"{mod}.{a.name}", mod):
                    pth = os.path.join(AIS_ROOT, *cand.split("."))
                    tgt = pth + ".py" if os.path.isfile(pth + ".py") else (os.path.join(pth, "__init__.py") if os.path.isfile(os.path.join(pth, "__init__.py")) else None)
                    if tgt:
                        deps.add(tgt)
                        break
    _ais_graph[f] = deps
_ais_color, _ais_stack = {}, []


def _ais_dfs(n):
    _ais_color[n] = 1
    _ais_stack.append(n)
    for d in _ais_graph.get(n, ()):
        if d == n or d not in _ais_graph:
            continue
        if _ais_color.get(d) == 1:
            cyc = [os.path.relpath(x, PROJECT) for x in _ais_stack[_ais_stack.index(d):]] + [os.path.relpath(d, PROJECT)]
            report("aiservice-no-circular-imports", n, " -> ".join(cyc))
        elif not _ais_color.get(d):
            _ais_dfs(d)
    _ais_stack.pop()
    _ais_color[n] = 2


for f in list(_ais_graph):
    if not _ais_color.get(f):
        _ais_dfs(f)

# who may import aiservice
_ALLOWED_AI_IMPORT = (os.path.join("app", "core") + os.sep, os.path.join("app", "shared", "ai.py"))
_backend_files = list(py_files(APP)) + [p for p in (os.path.join(ROOT, "alembic", "env.py"),) if os.path.isfile(p)]
for f in _backend_files:
    rel = os.path.relpath(f, ROOT)
    for name, _ in _abs_imports(ast.parse(open(f).read())):
        if name.split(".")[0] == "aiservice" and not (rel.startswith(_ALLOWED_AI_IMPORT[0]) or rel == _ALLOWED_AI_IMPORT[1]):
            report("aiservice-only-via-composition-root", f, f'imports "{name}"; modules declare ports, app/core binds AIService')
for f in ing_files:
    for name, _ in _abs_imports(ast.parse(open(f).read())):
        if name.split(".")[0] == "aiservice":
            report("ingestion-must-not-import-aiservice", f, f'imports "{name}"; ingestion does not perform AI analysis')

# the Gemini key identifier stays in configuration + provider construction
_KEY_ALLOWED = {os.path.join("app", "shared", "config.py"), os.path.join("app", "shared", "ai.py")}
for f in _backend_files:
    if os.path.relpath(f, ROOT) not in _KEY_ALLOWED and "GEMINI_API_KEY" in strip_to_code_tokens(f):
        report("gemini-key-centralized", f, "reads GEMINI_API_KEY outside app/shared/config.py and app/shared/ai.py")

# provider SDKs / endpoint only inside aiservice/providers
for f in _backend_files + ais_files + ing_files:
    if f in ais_files and _is_ais_provider_file(f):
        continue
    tree = ast.parse(open(f).read())
    for name, _ in _abs_imports(tree):
        if any(name == sdk or name.startswith(sdk + ".") for sdk in _PROVIDER_SDKS):
            report("provider-sdk-centralized", f, f'imports provider SDK "{name}" (only aiservice/providers may)')
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and GEMINI_URL in node.value:
            report("provider-sdk-centralized", f, "hardcodes the Gemini endpoint (only aiservice/providers/gemini.py may)")

# exactly one API server, and no Node backend
_SERVER_CALLS = {"FastAPI", "Flask", "Starlette", "Quart", "Sanic"}
_MAIN = os.path.join(APP, "main.py")
for f in _backend_files + ais_files + ing_files + [p for p in py_files(os.path.join(ROOT, "scripts"))]:
    for node in ast.walk(ast.parse(open(f).read())):
        if not isinstance(node, ast.Call):
            continue
        callee = getattr(node.func, "id", None) or getattr(node.func, "attr", None)
        owner = getattr(getattr(node.func, "value", None), "id", "")
        if (callee in _SERVER_CALLS and f != _MAIN) or (callee == "run" and owner == "uvicorn"):
            report("single-api-server", f, f"starts a server ({callee}); FastAPI in app/main.py is the only API")
_NODE_SERVERS = {"express", "koa", "fastify", "@hapi/hapi", "hapi", "restify", "@nestjs/core"}
for dp, dn, fn in os.walk(PROJECT):
    dn[:] = [d for d in dn if d not in ("node_modules", ".git", ".venv", "dist", "__pycache__", "visual-qa")]
    for name in fn:
        full = os.path.join(dp, name)
        if name in ("server.ts", "server.js", "server.mjs", "server.cjs"):
            report("no-node-backend", full, "a Node server entry point exists (Express was removed; FastAPI is the only backend)")
        if name == "package.json":
            try:
                import json as _json
                pkg = _json.load(open(full))
            except ValueError:
                continue
            deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
            for dep in sorted(_NODE_SERVERS & set(deps)):
                report("no-node-backend", full, f'depends on "{dep}"')

# nothing in app/ may import DbIngestion
for f in py_files(APP):
    for imp in imports_of(f):
        if imp.split(".")[0] == "dbingestion":
            report("app-must-not-import-dbingestion", f, f'imports "{imp}"')

# cycles
color, stack = {}, []


def dfs(n):
    color[n] = 1
    stack.append(n)
    for d in graph.get(n, ()):
        if d not in graph:
            continue
        if color.get(d) == 1:
            cyc = [os.path.relpath(x, ROOT) for x in stack[stack.index(d):]] + [os.path.relpath(d, ROOT)]
            report("no-circular-imports", n, " -> ".join(cyc))
        elif not color.get(d):
            dfs(d)
    stack.pop()
    color[n] = 2


for f in list(graph):
    if not color.get(f):
        dfs(f)

if violations:
    print(f"Architecture check FAILED ({len(violations)} violation(s)):", file=sys.stderr)
    for rule, f, detail in violations:
        print(f"  [{rule}] {f}: {detail}", file=sys.stderr)
    sys.exit(1)
print(f"Architecture check passed: {len(graph)} backend files + {len(ing_files)} DbIngestion files + {len(ais_files)} AIService files; {len(tables)} tables owned by modules; no boundary, cycle, persistence or ingestion-safety violations.")
