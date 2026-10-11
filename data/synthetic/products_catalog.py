"""Definitions of Insurance Products, Product Versions, Tariff Cells, and Wording Clauses A-F."""

from dataclasses import asdict, dataclass, field
from decimal import Decimal
import json
from pathlib import Path


@dataclass
class WordingClause:
    clause_id: str
    section: str  # A, B, C, D, E, F
    title: str
    text: str


@dataclass
class TariffCell:
    coverage_code: str
    base_rate_percent: float
    min_premium: float
    factors: dict[str, float] = field(default_factory=dict)


@dataclass
class ProductVersionDef:
    version: int
    version_code: str
    effective_from: str
    effective_to: str | None
    status: str
    clauses: list[WordingClause]
    tariffs: list[TariffCell]


@dataclass
class ProductDef:
    product_code: str
    name: str
    description: str
    line_of_business: str
    versions: list[ProductVersionDef]


PRODUCTS_DATA: list[ProductDef] = [
    # ----------------------------------------------------
    # MOTOR_OD (Kasko - Motor Own Damage)
    # ----------------------------------------------------
    ProductDef(
        product_code="MOTOR_OD",
        name="Motor Own Damage (Kasko)",
        description="Comprehensive physical damage, collision, theft, natural disaster, and vandalism coverage for private motor vehicles.",
        line_of_business="motor",
        versions=[
            # Version 1 (2025)
            ProductVersionDef(
                version=1,
                version_code="MOTOR_OD_V1_2025",
                effective_from="2025-01-01",
                effective_to="2025-12-31",
                status="archived",
                tariffs=[
                    TariffCell(
                        coverage_code="COLLISION_COMPREHENSIVE",
                        base_rate_percent=3.2,
                        min_premium=350.0,
                        factors={"driver_under_25": 1.25, "vehicle_age_gt_5": 1.15},
                    )
                ],
                clauses=[
                    WordingClause(
                        clause_id="MOTOR_OD:A.1",
                        section="A",
                        title="Collision and Overturning",
                        text="The insurer indemnifies direct physical damage to the insured vehicle caused by collision with other vehicles, stationary objects, animals, or overturning during lawful operation.",
                    ),
                    WordingClause(
                        clause_id="MOTOR_OD:A.2",
                        section="A",
                        title="Fire, Explosion, and Lightning",
                        text="Damage resulting from sudden fire, explosion, or direct lightning strike is covered, provided it did not originate from intentional arson by the policyholder.",
                    ),
                    WordingClause(
                        clause_id="MOTOR_OD:A.3",
                        section="A",
                        title="Natural Disasters",
                        text="Damage caused directly by storm, hurricane, flood, hail, torrential rainfall, or earthquake is covered upon official meteorological verification.",
                    ),
                    WordingClause(
                        clause_id="MOTOR_OD:A.4",
                        section="A",
                        title="Theft and Robbery",
                        text="Total loss of the vehicle or permanent loss of fitted manufacturer equipment resulting from theft, robbery, or carjacking is covered following official police report.",
                    ),
                    WordingClause(
                        clause_id="MOTOR_OD:A.5",
                        section="A",
                        title="Malicious Acts of Third Parties",
                        text="Physical damage caused by intentional vandalism or malicious acts of unidentified third parties while the vehicle is lawfully parked is covered.",
                    ),
                    WordingClause(
                        clause_id="MOTOR_OD:B.1",
                        section="B",
                        title="War and Civil Commotion",
                        text="Loss or damage directly or indirectly occasioned by war, invasion, hostilities, civil war, rebellion, revolution, or nuclear contamination is strictly excluded.",
                    ),
                    WordingClause(
                        clause_id="MOTOR_OD:B.2",
                        section="B",
                        title="Intentional Damage and Gross Negligence",
                        text="Loss caused by the deliberate action, fraud, or gross negligence of the insured, registered drivers, or authorized custodians is excluded from coverage.",
                    ),
                    WordingClause(
                        clause_id="MOTOR_OD:B.3",
                        section="B",
                        title="Driving Under the Influence",
                        text="Any accident occurring while the operating driver is under the influence of alcohol (blood alcohol level > 0.0 g/l), narcotics, or psychotropic medication is strictly excluded.",
                    ),
                    WordingClause(
                        clause_id="MOTOR_OD:B.4",
                        section="B",
                        title="Unlicensed Driver",
                        text="No coverage applies if the driver operating the vehicle at the time of loss lacked a valid, unexpired driver license appropriate for the vehicle category.",
                    ),
                    WordingClause(
                        clause_id="MOTOR_OD:B.5",
                        section="B",
                        title="Speed Contests and Illegal Use",
                        text="Use of the insured vehicle in authorized or unauthorized racing, rallies, speed testing, or unlawful transportation of contraband is strictly excluded.",
                    ),
                    WordingClause(
                        clause_id="MOTOR_OD:B.6",
                        section="B",
                        title="Wear and Tear and Mechanical Breakdown",
                        text="Gradual wear and tear, corrosion, manufacturer defects, tire puncture without body collision, and internal mechanical or electrical failures are excluded.",
                    ),
                    WordingClause(
                        clause_id="MOTOR_OD:C.1",
                        section="C",
                        title="Mitigation of Loss",
                        text="In the event of an incident, the insured must take all reasonable precautions to protect the vehicle and mitigate further damage.",
                    ),
                    WordingClause(
                        clause_id="MOTOR_OD:C.2",
                        section="C",
                        title="Notice of Claim (2025 Wording)",
                        text="The insured must notify the insurer of any loss or incident within 3 business days of its occurrence. Failure to notify within this period without justifiable force majeure may justify denial.",
                    ),
                    WordingClause(
                        clause_id="MOTOR_OD:C.3",
                        section="C",
                        title="Police Notification",
                        text="All traffic accidents involving other parties, theft, vandalism, or bodily injury must be reported immediately to the State Traffic Police prior to moving the vehicle.",
                    ),
                    WordingClause(
                        clause_id="MOTOR_OD:D.1",
                        section="D",
                        title="Valuation and Repair",
                        text="Partial loss repairs are indemnified based on approved itemized estimates from certified partner repair centers using authorized replacement parts.",
                    ),
                    WordingClause(
                        clause_id="MOTOR_OD:D.2",
                        section="D",
                        title="Constructive Total Loss Threshold (2025 Wording)",
                        text="If repair costs equal or exceed 70% of the vehicle actual market value, the loss is deemed a Constructive Total Loss. Payout equals Sum Insured minus salvage value minus deductible.",
                    ),
                    WordingClause(
                        clause_id="MOTOR_OD:D.3",
                        section="D",
                        title="Application of Deductible (2025 Wording)",
                        text="An unconditional deductible of 200 AZN is subtracted from the gross payable indemnification amount for each independent partial loss claim.",
                    ),
                    WordingClause(
                        clause_id="MOTOR_OD:E.1",
                        section="E",
                        title="Subrogation Rights",
                        text="Upon payment of any claim, the insurer is subrogated to all rights and remedies of the insured against liable third parties up to the amount paid.",
                    ),
                    WordingClause(
                        clause_id="MOTOR_OD:F.1",
                        section="F",
                        title="Cancellation and Pro-Rata Refund",
                        text="Upon mid-term cancellation by the policyholder, unearned premium is refunded on a daily pro-rata basis minus a 25 AZN administrative fee, provided no claims have been filed.",
                    ),
                ],
            ),
            # Version 2 (2026 - Current Wording)
            ProductVersionDef(
                version=2,
                version_code="MOTOR_OD_V2_2026",
                effective_from="2026-01-01",
                effective_to=None,
                status="published",
                tariffs=[
                    TariffCell(
                        coverage_code="COLLISION_COMPREHENSIVE",
                        base_rate_percent=3.4,
                        min_premium=380.0,
                        factors={"driver_under_25": 1.30, "vehicle_age_gt_5": 1.20},
                    )
                ],
                clauses=[
                    WordingClause(
                        clause_id="MOTOR_OD:A.1",
                        section="A",
                        title="Collision and Overturning",
                        text="The insurer indemnifies direct physical damage to the insured vehicle caused by collision with other vehicles, stationary objects, animals, or overturning during lawful operation.",
                    ),
                    WordingClause(
                        clause_id="MOTOR_OD:A.2",
                        section="A",
                        title="Fire, Explosion, and Lightning",
                        text="Damage resulting from sudden fire, explosion, or direct lightning strike is covered, provided it did not originate from intentional arson by the policyholder.",
                    ),
                    WordingClause(
                        clause_id="MOTOR_OD:A.3",
                        section="A",
                        title="Natural Disasters",
                        text="Damage caused directly by storm, hurricane, flood, hail, torrential rainfall, or earthquake is covered upon official meteorological verification.",
                    ),
                    WordingClause(
                        clause_id="MOTOR_OD:A.4",
                        section="A",
                        title="Theft and Robbery",
                        text="Total loss of the vehicle or permanent loss of fitted manufacturer equipment resulting from theft, robbery, or carjacking is covered following official police report.",
                    ),
                    WordingClause(
                        clause_id="MOTOR_OD:A.5",
                        section="A",
                        title="Malicious Acts of Third Parties",
                        text="Physical damage caused by intentional vandalism or malicious acts of unidentified third parties while the vehicle is lawfully parked is covered.",
                    ),
                    WordingClause(
                        clause_id="MOTOR_OD:B.1",
                        section="B",
                        title="War and Civil Commotion",
                        text="Loss or damage directly or indirectly occasioned by war, invasion, hostilities, civil war, rebellion, revolution, or nuclear contamination is strictly excluded.",
                    ),
                    WordingClause(
                        clause_id="MOTOR_OD:B.2",
                        section="B",
                        title="Intentional Damage and Gross Negligence",
                        text="Loss caused by the deliberate action, fraud, or gross negligence of the insured, registered drivers, or authorized custodians is excluded from coverage.",
                    ),
                    WordingClause(
                        clause_id="MOTOR_OD:B.3",
                        section="B",
                        title="Driving Under the Influence",
                        text="Any accident occurring while the operating driver is under the influence of alcohol (blood alcohol level > 0.0 g/l), narcotics, or psychotropic medication is strictly excluded.",
                    ),
                    WordingClause(
                        clause_id="MOTOR_OD:B.4",
                        section="B",
                        title="Unlicensed Driver",
                        text="No coverage applies if the driver operating the vehicle at the time of loss lacked a valid, unexpired driver license appropriate for the vehicle category.",
                    ),
                    WordingClause(
                        clause_id="MOTOR_OD:B.5",
                        section="B",
                        title="Speed Contests and Illegal Use",
                        text="Use of the insured vehicle in authorized or unauthorized racing, rallies, speed testing, or unlawful transportation of contraband is strictly excluded.",
                    ),
                    WordingClause(
                        clause_id="MOTOR_OD:B.6",
                        section="B",
                        title="Wear and Tear and Mechanical Breakdown",
                        text="Gradual wear and tear, corrosion, manufacturer defects, tire puncture without body collision, and internal mechanical or electrical failures are excluded.",
                    ),
                    WordingClause(
                        clause_id="MOTOR_OD:B.7",
                        section="B",
                        title="Cyber and Unauthorized Software Modification Exclusion (New in 2026)",
                        text="Any incident directly resulting from unauthorized ECU firmware tampering, aftermarket electronic hacking, or remote cyber interference is strictly excluded.",
                    ),
                    WordingClause(
                        clause_id="MOTOR_OD:C.1",
                        section="C",
                        title="Mitigation of Loss",
                        text="In the event of an incident, the insured must take all reasonable precautions to protect the vehicle and mitigate further damage.",
                    ),
                    WordingClause(
                        clause_id="MOTOR_OD:C.2",
                        section="C",
                        title="Notice of Claim (2026 Wording - Stricter 2-Day Deadline)",
                        text="The insured must notify the insurer electronically via mobile app or portal within 2 business days of its occurrence. Claims submitted after 2 business days without documented medical emergency are denied.",
                    ),
                    WordingClause(
                        clause_id="MOTOR_OD:C.3",
                        section="C",
                        title="Police Notification",
                        text="All traffic accidents involving other parties, theft, vandalism, or bodily injury must be reported immediately to the State Traffic Police prior to moving the vehicle.",
                    ),
                    WordingClause(
                        clause_id="MOTOR_OD:D.1",
                        section="D",
                        title="Valuation and Repair",
                        text="Partial loss repairs are indemnified based on approved itemized estimates from certified partner repair centers using authorized replacement parts.",
                    ),
                    WordingClause(
                        clause_id="MOTOR_OD:D.2",
                        section="D",
                        title="Constructive Total Loss Threshold (2026 Wording - 75%)",
                        text="If repair costs equal or exceed 75% of the vehicle actual market value, the loss is deemed a Constructive Total Loss. Payout equals Sum Insured minus salvage value minus deductible.",
                    ),
                    WordingClause(
                        clause_id="MOTOR_OD:D.3",
                        section="D",
                        title="Application of Deductible (2026 Wording - 250 AZN)",
                        text="An unconditional deductible of 250 AZN is subtracted from the gross payable indemnification amount for each independent partial loss claim.",
                    ),
                    WordingClause(
                        clause_id="MOTOR_OD:E.1",
                        section="E",
                        title="Subrogation Rights",
                        text="Upon payment of any claim, the insurer is subrogated to all rights and remedies of the insured against liable third parties up to the amount paid.",
                    ),
                    WordingClause(
                        clause_id="MOTOR_OD:F.1",
                        section="F",
                        title="Cancellation and Pro-Rata Refund",
                        text="Upon mid-term cancellation by the policyholder, unearned premium is refunded on a daily pro-rata basis minus a 25 AZN administrative fee, provided no claims have been filed.",
                    ),
                ],
            ),
        ],
    ),
    # ----------------------------------------------------
    # MOTOR_TPL (İcbari Avto - Third Party Liability)
    # ----------------------------------------------------
    ProductDef(
        product_code="MOTOR_TPL",
        name="Compulsory Motor Third-Party Liability",
        description="Statutory insurance covering third-party bodily injury and property damage caused by the operation of the motor vehicle.",
        line_of_business="motor",
        versions=[
            ProductVersionDef(
                version=1,
                version_code="MOTOR_TPL_V1_2026",
                effective_from="2026-01-01",
                effective_to=None,
                status="published",
                tariffs=[
                    TariffCell(
                        coverage_code="TPL_STATUTORY",
                        base_rate_percent=0.5,
                        min_premium=50.0,
                        factors={"engine_gt_2000": 1.25},
                    )
                ],
                clauses=[
                    WordingClause(
                        clause_id="MOTOR_TPL:A.1",
                        section="A",
                        title="Scope of Statutory Liability",
                        text="Indemnifies civil liability for damage caused to third-party property up to 5,000 AZN and third-party bodily injury up to 50,000 AZN arising from road traffic collisions.",
                    ),
                    WordingClause(
                        clause_id="MOTOR_TPL:B.1",
                        section="B",
                        title="Insured Own Vehicle Exclusion",
                        text="Damage to the insured vehicle itself or property owned by the policyholder is strictly excluded from third-party liability cover.",
                    ),
                    WordingClause(
                        clause_id="MOTOR_TPL:C.1",
                        section="C",
                        title="Statutory Notice",
                        text="Notice must be given within statutory timeline with police protocol identifying fault.",
                    ),
                    WordingClause(
                        clause_id="MOTOR_TPL:D.1",
                        section="D",
                        title="Third-Party Settlement",
                        text="Indemnification is disbursed directly to damaged third parties or their authorized heirs.",
                    ),
                ],
            )
        ],
    ),
    # ----------------------------------------------------
    # HOME (Property Insurance)
    # ----------------------------------------------------
    ProductDef(
        product_code="HOME",
        name="Residential Property Insurance",
        description="Coverage for residential buildings and contents against fire, explosion, water pipe bursts, natural disasters, and burglary.",
        line_of_business="property",
        versions=[
            ProductVersionDef(
                version=1,
                version_code="HOME_V1_2026",
                effective_from="2026-01-01",
                effective_to=None,
                status="published",
                tariffs=[
                    TariffCell(
                        coverage_code="HOME_ALL_RISKS",
                        base_rate_percent=0.25,
                        min_premium=120.0,
                        factors={"wooden_structure": 1.5},
                    )
                ],
                clauses=[
                    WordingClause(
                        clause_id="HOME:A.1",
                        section="A",
                        title="Fire and Explosion",
                        text="Direct loss or damage caused by fire, lightning, or domestic gas explosion to insured building structure and fixtures.",
                    ),
                    WordingClause(
                        clause_id="HOME:A.2",
                        section="A",
                        title="Water Pipe Burst and Plumbing Leaks",
                        text="Sudden and accidental discharge or leakage of water from interior plumbing systems, heating apparatus, or sanitary installations.",
                    ),
                    WordingClause(
                        clause_id="HOME:A.3",
                        section="A",
                        title="Natural Disasters and Earthquake",
                        text="Damage caused directly by earthquake, land subsidence, or severe windstorm exceeding 60 km/h.",
                    ),
                    WordingClause(
                        clause_id="HOME:B.1",
                        section="B",
                        title="Unoccupied Property Exclusion",
                        text="Damage resulting from water pipe freezing or burglary occurring when premises have been left unoccupied for more than 30 consecutive days.",
                    ),
                    WordingClause(
                        clause_id="HOME:C.1",
                        section="C",
                        title="Emergency Services Protocol",
                        text="Mandatory protocol from State Fire Service or relevant emergency ministry within 5 days.",
                    ),
                    WordingClause(
                        clause_id="HOME:D.1",
                        section="D",
                        title="Home Partial Loss Deductible",
                        text="Standard deductible of 150 AZN applied to each partial property damage claim.",
                    ),
                ],
            )
        ],
    ),
]


def save_products_to_disk(target_dir: Path) -> Path:
    """Exports structured products to JSON for seeding and evaluation."""
    target_dir.mkdir(parents=True, exist_ok=True)
    out_file = target_dir / "products.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump([asdict(p) for p in PRODUCTS_DATA], f, indent=2)
    return out_file
