import os

modules = [
    "platform", "party", "product", "policy", "claims", "sales",
    "underwriting", "finance", "fraud", "compliance", "service", "reinsurance"
]

for m in modules:
    mdir = os.path.join("backend", "app", "modules", m)
    os.makedirs(mdir, exist_ok=True)
    init_f = os.path.join(mdir, "__init__.py")
    pub_f = os.path.join(mdir, "public.py")
    if not os.path.exists(init_f):
        with open(init_f, "w", encoding="utf-8") as f:
            f.write(f'"""{m.capitalize()} bounded context module."""\n')
    if not os.path.exists(pub_f):
        with open(pub_f, "w", encoding="utf-8") as f:
            f.write(
                f'"""Public API and contracts for the {m} module.\n'
                f'Other modules must import ONLY from this file.\n"""\n\n'
                f'__all__: list[str] = []\n'
            )

for d in [
    os.path.join("backend", "app", "api"),
    os.path.join("backend", "app", "shared"),
    os.path.join("backend", "tests", "unit"),
    os.path.join("backend", "tests", "integration"),
    os.path.join("backend", "tests", "architecture"),
    os.path.join("data", "synthetic"),
    "evals",
    "scripts"
]:
    os.makedirs(d, exist_ok=True)
    if "tests" in d or "app" in d:
        init_file = os.path.join(d, "__init__.py")
        if not os.path.exists(init_file):
            with open(init_file, "w", encoding="utf-8") as f:
                f.write("")

with open(os.path.join("backend", "app", "__init__.py"), "w", encoding="utf-8") as f:
    f.write('"""InsurAI Backend Application Package."""\n')

print("Module structure created successfully!")
