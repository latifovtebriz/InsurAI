"""Product domain service managing insurance products, versions, tariffs, and four-eyes publication."""

from datetime import UTC, date, datetime
from typing import Any

from app.modules.platform.public import InsurAIException
from app.modules.product.models import Product, ProductVersion
from sqlalchemy import or_, select
from sqlalchemy.orm import Session


def utcnow() -> datetime:
    return datetime.now(UTC)


class FourEyesViolationError(InsurAIException):
    """Raised when publication is attempted without distinct reviewer."""

    def __init__(
        self,
        message: str = "Four-eyes principle violation: Reviewer cannot be the same as creator.",
    ) -> None:
        super().__init__(status_code=400, title="Four-Eyes Principle Violation", detail=message)


class ProductService:
    """Service managing product definitions, effective-dated versions, and publication governance."""

    def create_product(
        self,
        session: Session,
        product_code: str,
        name: str,
        description: str,
        line_of_business: str,
        is_active: bool = True,
    ) -> Product:
        existing = session.scalars(
            select(Product).where(Product.product_code == product_code)
        ).first()
        if existing:
            return existing

        prod = Product(
            product_code=product_code,
            name=name,
            description=description,
            line_of_business=line_of_business,
            is_active=is_active,
        )
        session.add(prod)
        session.commit()
        session.refresh(prod)
        return prod

    def get_product_by_code(self, session: Session, product_code: str) -> Product | None:
        return session.scalars(select(Product).where(Product.product_code == product_code)).first()

    def list_products(self, session: Session) -> list[Product]:
        return list(session.scalars(select(Product)).all())

    def create_product_version(
        self,
        session: Session,
        product_code: str,
        version: int,
        version_code: str,
        effective_from: date,
        tariffs: list[dict[str, Any]],
        clauses: list[dict[str, Any]],
        created_by: str,
        effective_to: date | None = None,
        status: str = "draft",
    ) -> ProductVersion:
        prod = self.get_product_by_code(session, product_code)
        if not prod:
            raise InsurAIException(
                status_code=404,
                title="Product Not Found",
                detail=f"Product '{product_code}' not found.",
            )

        p_ver = ProductVersion(
            product_id=prod.id,
            product_code=product_code,
            version=version,
            version_code=version_code,
            effective_from=effective_from,
            effective_to=effective_to,
            status=status,
            tariffs=tariffs,
            clauses=clauses,
            created_by=created_by,
        )
        session.add(p_ver)
        session.commit()
        session.refresh(p_ver)
        return p_ver

    def publish_product_version(
        self,
        session: Session,
        version_id: str,
        reviewer_id: str,
    ) -> ProductVersion:
        """Enforces the four-eyes publication rule: reviewer must be distinct from creator."""
        p_ver = session.get(ProductVersion, version_id)
        if not p_ver:
            raise InsurAIException(
                status_code=404,
                title="Version Not Found",
                detail=f"Version ID '{version_id}' not found.",
            )

        if p_ver.created_by == reviewer_id:
            raise FourEyesViolationError("Publisher cannot self-approve their own product version.")

        p_ver.status = "published"
        p_ver.reviewed_by = reviewer_id
        p_ver.published_at = utcnow()
        session.commit()
        session.refresh(p_ver)
        return p_ver

    def get_active_version(
        self,
        session: Session,
        product_code: str,
        as_of_date: date,
    ) -> ProductVersion | None:
        """Retrieves the published product version in force for a specific date."""
        query = (
            select(ProductVersion)
            .where(
                ProductVersion.product_code == product_code,
                ProductVersion.status == "published",
                ProductVersion.effective_from <= as_of_date,
                or_(
                    ProductVersion.effective_to.is_(None),
                    ProductVersion.effective_to >= as_of_date,
                ),
            )
            .order_by(ProductVersion.version.desc())
        )
        return session.scalars(query).first()


product_service = ProductService()
