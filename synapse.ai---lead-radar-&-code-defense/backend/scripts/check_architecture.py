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
    r"(lead|repo|repository|voice|interview|leaderboard|candidate|outreach|ingest|ingestion|verdict|benchmark)",
    re.I,
)

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
        for name in strip_to_code_tokens(f):
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
print(f"Architecture check passed: {len(graph)} files; {len(tables)} tables owned by modules; no boundary, cycle or persistence violations.")
