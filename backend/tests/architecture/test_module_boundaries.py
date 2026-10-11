"""Architecture tests enforcing module boundary isolation."""

import ast
from pathlib import Path


def get_module_imports(file_path: Path) -> list[str]:
    """Extracts all imported module paths from a Python file using AST."""
    with open(file_path, encoding="utf-8") as f:
        try:
            tree = ast.parse(f.read(), filename=str(file_path))
        except SyntaxError:
            return []

    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported.append(node.module)
    return imported


def check_boundary_violations(base_dir: Path) -> list[str]:
    """
    Checks that no module imports internal implementation of another module.
    Permitted:
      - from app.modules.<other>.public import ...
      - from app.modules.<other> import public
    Forbidden:
      - from app.modules.<other>.<internal> import ...
    """
    modules_dir = base_dir / "backend" / "app" / "modules"
    if not modules_dir.exists():
        return []

    violations: list[str] = []

    for source_file in modules_dir.rglob("*.py"):
        rel = source_file.relative_to(modules_dir)
        source_module = rel.parts[0]

        for imp in get_module_imports(source_file):
            if "app.modules." in imp:
                parts = imp.split("app.modules.")[1].split(".")
                target_module = parts[0]

                if target_module != source_module:
                    # Target is another module
                    if len(parts) > 1 and parts[1] != "public":
                        violations.append(
                            f"{source_file} imports internal '{imp}' from module '{target_module}'. "
                            f"Must only import through '{target_module}.public'."
                        )

    return violations


def test_no_module_imports_another_modules_internals() -> None:
    """Verifies that across all modules, inter-module imports only use public.py."""
    repo_root = Path(__file__).resolve().parent.parent.parent.parent
    violations = check_boundary_violations(repo_root)
    assert not violations, "Architecture boundary violations detected:\n" + "\n".join(violations)


def test_boundary_checker_detects_deliberate_violation(tmp_path: Path) -> None:
    """Tests the architecture checker itself by giving it a simulated violation."""
    fake_modules = tmp_path / "backend" / "app" / "modules"
    fake_mod_a = fake_modules / "module_a"
    fake_mod_b = fake_modules / "module_b"
    fake_mod_a.mkdir(parents=True)
    fake_mod_b.mkdir(parents=True)

    # File in module_a illegally importing internal file from module_b
    test_file = fake_mod_a / "service.py"
    test_file.write_text(
        "from app.modules.module_b.internal_secret import secret_fn\n", encoding="utf-8"
    )

    violations = check_boundary_violations(tmp_path)
    assert len(violations) == 1
    assert "imports internal 'app.modules.module_b.internal_secret'" in violations[0]
