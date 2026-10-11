"""Party domain service for managing parties, assets, and intermediaries."""

from decimal import Decimal
from typing import Any

from app.modules.party.models import Intermediary, Party, Property, Vehicle
from sqlalchemy import select
from sqlalchemy.orm import Session


class PartyService:
    """Service handling CRUD and KYC status for parties, vehicles, and properties."""

    def create_party(
        self,
        session: Session,
        party_type: str,
        tax_id: str,
        email: str,
        phone: str,
        address: str,
        first_name: str | None = None,
        last_name: str | None = None,
        company_name: str | None = None,
        kyc_status: str = "verified",
        metadata_json: dict[str, Any] | None = None,
    ) -> Party:
        party = Party(
            party_type=party_type,
            tax_id=tax_id,
            email=email,
            phone=phone,
            address=address,
            first_name=first_name,
            last_name=last_name,
            company_name=company_name,
            kyc_status=kyc_status,
            metadata_json=metadata_json or {},
        )
        session.add(party)
        session.commit()
        session.refresh(party)
        return party

    def get_party_by_id(self, session: Session, party_id: str) -> Party | None:
        return session.get(Party, party_id)

    def get_party_by_tax_id(self, session: Session, tax_id: str) -> Party | None:
        return session.scalars(select(Party).where(Party.tax_id == tax_id)).first()

    def update_kyc_status(self, session: Session, party_id: str, status: str) -> Party | None:
        party = session.get(Party, party_id)
        if party:
            party.kyc_status = status
            session.commit()
            session.refresh(party)
        return party

    def create_vehicle(
        self,
        session: Session,
        owner_party_id: str,
        vin: str,
        registration_number: str,
        make: str,
        model: str,
        manufacture_year: int,
        engine_capacity_cc: int,
        market_value: Decimal,
    ) -> Vehicle:
        vehicle = Vehicle(
            owner_party_id=owner_party_id,
            vin=vin,
            registration_number=registration_number,
            make=make,
            model=model,
            manufacture_year=manufacture_year,
            engine_capacity_cc=engine_capacity_cc,
            market_value=market_value,
        )
        session.add(vehicle)
        session.commit()
        session.refresh(vehicle)
        return vehicle

    def get_vehicle_by_id(self, session: Session, vehicle_id: str) -> Vehicle | None:
        return session.get(Vehicle, vehicle_id)

    def get_vehicle_by_vin(self, session: Session, vin: str) -> Vehicle | None:
        return session.scalars(select(Vehicle).where(Vehicle.vin == vin)).first()

    def list_vehicles_by_owner(self, session: Session, owner_party_id: str) -> list[Vehicle]:
        return list(
            session.scalars(select(Vehicle).where(Vehicle.owner_party_id == owner_party_id)).all()
        )

    def create_property(
        self,
        session: Session,
        owner_party_id: str,
        cadastral_code: str,
        address: str,
        build_year: int,
        construction_type: str,
        floor_area_sqm: Decimal,
        estimated_value: Decimal,
    ) -> Property:
        prop = Property(
            owner_party_id=owner_party_id,
            cadastral_code=cadastral_code,
            address=address,
            build_year=build_year,
            construction_type=construction_type,
            floor_area_sqm=floor_area_sqm,
            estimated_value=estimated_value,
        )
        session.add(prop)
        session.commit()
        session.refresh(prop)
        return prop

    def get_property_by_id(self, session: Session, property_id: str) -> Property | None:
        return session.get(Property, property_id)

    def get_property_by_cadastral_code(
        self, session: Session, cadastral_code: str
    ) -> Property | None:
        return session.scalars(
            select(Property).where(Property.cadastral_code == cadastral_code)
        ).first()

    def list_properties_by_owner(self, session: Session, owner_party_id: str) -> list[Property]:
        return list(
            session.scalars(select(Property).where(Property.owner_party_id == owner_party_id)).all()
        )

    def create_intermediary(
        self,
        session: Session,
        party_id: str,
        broker_code: str,
        license_number: str,
        commission_rate: Decimal = Decimal("0.1000"),
    ) -> Intermediary:
        broker = Intermediary(
            party_id=party_id,
            broker_code=broker_code,
            license_number=license_number,
            commission_rate=commission_rate,
        )
        session.add(broker)
        session.commit()
        session.refresh(broker)
        return broker

    def get_intermediary_by_code(self, session: Session, broker_code: str) -> Intermediary | None:
        return session.scalars(
            select(Intermediary).where(Intermediary.broker_code == broker_code)
        ).first()


party_service = PartyService()
