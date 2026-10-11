"""Public API for the product module.
Other modules must import ONLY from this file.
"""

from app.modules.product.models import Product, ProductVersion
from app.modules.product.service import (
    FourEyesViolationError,
    ProductService,
    product_service,
)

__all__: list[str] = [
    "Product",
    "ProductVersion",
    "ProductService",
    "product_service",
    "FourEyesViolationError",
]
