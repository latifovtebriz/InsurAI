"""Script to regenerate identical synthetic datasets from a deterministic seed."""

import sys
from pathlib import Path

# Add project root to path
repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root))

from data.synthetic.generator import create_synthetic_world, save_synthetic_world_to_disk  # noqa: E402
from data.synthetic.products_catalog import save_products_to_disk  # noqa: E402


def main() -> int:
    print("Generating deterministic synthetic insurance data...")
    out_dir = repo_root / "data" / "synthetic"

    # Save products catalog
    save_products_to_disk(out_dir)

    # Generate world with fixed seed
    world = create_synthetic_world(seed=42)
    stats = save_synthetic_world_to_disk(world, out_dir)

    print("\nGeneration complete! Record counts:")
    for key, count in stats.items():
        print(f"  {key:25s}: {count}")

    # Verify counts meet acceptance criteria
    assert stats["motor_od_claims"] >= 80, "MOTOR_OD must have at least 80 scenarios"
    assert stats["motor_tpl_claims"] >= 25, "MOTOR_TPL must have at least 25 scenarios"
    assert stats["home_claims"] >= 25, "HOME must have at least 25 scenarios"
    total_claims = stats["motor_od_claims"] + stats["motor_tpl_claims"] + stats["home_claims"]
    assert total_claims >= 130, "Total claims must meet benchmark"
    print(f"\n[PASSED] All acceptance criteria counts satisfied (Total Claims: {total_claims}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
