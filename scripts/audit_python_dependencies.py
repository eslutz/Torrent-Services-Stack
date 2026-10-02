"""Keep active Python tooling dependency-free and auditable with the stdlib."""

import ast
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
MANIFESTS = (
    "requirements.txt",
    "requirements-dev.txt",
    "pyproject.toml",
    "Pipfile",
    "Pipfile.lock",
    "poetry.lock",
    "uv.lock",
)


def active_sources():
    sources = [ROOT / "stack_renderer.py", ROOT / "scripts/verify", Path(__file__)]
    sources.extend((ROOT / "tests").rglob("*.py"))
    sources.extend((ROOT / "templates").rglob("*.py"))
    return sorted({path.resolve() for path in sources if path.is_file()})


def imported_roots(source):
    tree = ast.parse(source.read_text(), filename=str(source))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name.split(".", maxsplit=1)[0]
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            yield node.module.split(".", maxsplit=1)[0]


def main():
    sources = active_sources()
    local_modules = {path.stem for path in sources}
    standard_library = sys.stdlib_module_names
    unexpected = []
    for source in sources:
        for module in imported_roots(source):
            if module not in standard_library and module not in local_modules:
                unexpected.append(f"{source.relative_to(ROOT)} imports {module}")

    manifests = [name for name in MANIFESTS if (ROOT / name).exists()]
    if unexpected or manifests:
        for issue in unexpected:
            print(issue, file=sys.stderr)
        if manifests:
            print("Python dependency manifests require a reviewed audit update: "
                  + ", ".join(manifests), file=sys.stderr)
        return 1

    print(f"Audited {len(sources)} active Python files: stdlib imports only; no dependency manifests")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
