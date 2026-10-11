"""Unit and consistency tests for synthetic data generation and domain rules."""

from dataclasses import asdict

from data.synthetic.generator import create_synthetic_world
from data.synthetic.products_catalog import PRODUCTS_DATA


def test_generator_determinism() -> None:
    """Verifies that running the generator with the same seed produces identical output."""
    world_1 = create_synthetic_world(seed=42)
    world_2 = create_synthetic_world(seed=42)

    assert len(world_1.motor_od_claims) == len(world_2.motor_od_claims)
    assert len(world_1.policies) == len(world_2.policies)

    # Compare exact JSON serializations
    dict_1 = asdict(world_1)
    dict_2 = asdict(world_2)
    assert dict_1 == dict_2


def test_motor_od_scenarios_meet_appendix_g6() -> None:
    """Verifies scenario counts, category coverage, and injection cases per Appendix G.6."""
    world = create_synthetic_world(seed=42)
    od_claims = world.motor_od_claims

    assert len(od_claims) >= 80

    categories = {c.category for c in od_claims}
    expected_categories = {
        "clean_covered_collision",
        "amount_above_sum_insured_or_edge_deductible",
        "policy_expired_or_not_started",
        "excluded_cause_stated_clearly",
        "excluded_cause_hidden_in_doc",
        "late_notification_beyond_allowed",
        "wear_and_tear_disguised",
        "theft_fire_natural_disaster",
        "missing_key_information",
        "fraud_indicators",
        "prompt_injection_attempts",
        "ambiguous_cases",
    }
    assert expected_categories.issubset(categories)

    # Prompt injection cases
    injection_cases = [c for c in od_claims if c.is_injection_attempt]
    assert len(injection_cases) >= 4
    for inj in injection_cases:
        # Crucial safety invariant: Injection must NEVER be labeled approve!
        assert inj.expected_recommendation != "approve"


def test_held_out_splits_and_leakage_safety() -> None:
    """Ensures test split is held out (at least 20%) and smoke subset exists."""
    world = create_synthetic_world(seed=42)
    all_claims = world.motor_od_claims + world.motor_tpl_claims + world.home_claims

    dev_count = sum(1 for c in all_claims if c.split == "dev")
    test_count = sum(1 for c in all_claims if c.split == "test")
    smoke_count = sum(1 for c in all_claims if c.split == "smoke")

    assert smoke_count > 0
    assert test_count >= len(all_claims) * 0.20  # At least 20% held-out
    assert dev_count + test_count + smoke_count == len(all_claims)


def test_referential_integrity_and_synthetic_privacy() -> None:
    """Ensures all parties and data are strictly synthetic with no real PII."""
    world = create_synthetic_world(seed=42)

    for party in world.parties:
        # All tax IDs must start with synthetic marker
        assert party["tax_id"].startswith("SYN")
        # All emails must use synthetic domain
        assert party["email"].endswith("@synthetic-domain.test")

    # Policy references
    policy_numbers = {p["policy_number"] for p in world.policies}
    for claim in world.motor_od_claims:
        assert claim.policy_number in policy_numbers


def test_effective_dating_clauses_difference() -> None:
    """Verifies that Motor OD v1 (2025) and v2 (2026) have distinct wording clauses for time-travel."""
    motor_od = next(p for p in PRODUCTS_DATA if p.product_code == "MOTOR_OD")
    assert len(motor_od.versions) >= 2

    v1 = next(v for v in motor_od.versions if v.version == 1)
    v2 = next(v for v in motor_od.versions if v.version == 2)

    v1_clause_ids = {c.clause_id for c in v1.clauses}
    v2_clause_ids = {c.clause_id for c in v2.clauses}

    # v2 introduced cyber exclusion
    assert "MOTOR_OD:B.7" in v2_clause_ids
    assert "MOTOR_OD:B.7" not in v1_clause_ids

    # Notice period differs
    v1_c2 = next(c for c in v1.clauses if c.clause_id == "MOTOR_OD:C.2")
    v2_c2 = next(c for c in v2.clauses if c.clause_id == "MOTOR_OD:C.2")
    assert "3 business days" in v1_c2.text
    assert "2 business days" in v2_c2.text
