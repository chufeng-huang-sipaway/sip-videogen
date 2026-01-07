"""Brand Marketing Advisor - single agent with skills architecture."""

# Lazy imports to avoid circular dependencies
# Import BrandAdvisor when needed: from sip_studio.advisor.agent import BrandAdvisor

__all__ = ["BrandAdvisor"]


def __getattr__(name: str):
    """Lazy import for BrandAdvisor."""
    if name == "BrandAdvisor":
        from sip_studio.advisor.agent import BrandAdvisor

        return BrandAdvisor
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
