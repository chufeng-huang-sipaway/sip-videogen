"""Studio bridge services.

Keep imports lazy so lightweight modules (like `image_status`) can be used
without importing optional heavy runtime dependencies.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

__all__ = [
    "AssetService",
    "BrandService",
    "ChatService",
    "DocumentService",
    "ImageStatusService",
    "ProductService",
    "ProjectService",
    "ResearchService",
    "StyleReferenceService",
    "UpdateService",
]

if TYPE_CHECKING:
    from .asset_service import AssetService as AssetService
    from .brand_service import BrandService as BrandService
    from .chat_service import ChatService as ChatService
    from .document_service import DocumentService as DocumentService
    from .image_status import ImageStatusService as ImageStatusService
    from .product_service import ProductService as ProductService
    from .project_service import ProjectService as ProjectService
    from .research_service import ResearchService as ResearchService
    from .style_reference_service import StyleReferenceService as StyleReferenceService
    from .update_service import UpdateService as UpdateService


def __getattr__(name: str):
    if name == "AssetService":
        from .asset_service import AssetService

        return AssetService
    if name == "BrandService":
        from .brand_service import BrandService

        return BrandService
    if name == "ChatService":
        from .chat_service import ChatService

        return ChatService
    if name == "DocumentService":
        from .document_service import DocumentService

        return DocumentService
    if name == "ImageStatusService":
        from .image_status import ImageStatusService

        return ImageStatusService
    if name == "ProductService":
        from .product_service import ProductService

        return ProductService
    if name == "ProjectService":
        from .project_service import ProjectService

        return ProjectService
    if name == "ResearchService":
        from .research_service import ResearchService

        return ResearchService
    if name == "StyleReferenceService":
        from .style_reference_service import StyleReferenceService

        return StyleReferenceService
    if name == "UpdateService":
        from .update_service import UpdateService

        return UpdateService
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
