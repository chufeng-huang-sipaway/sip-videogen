"""Shared state for bridge services."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path
    from sip_videogen.advisor.agent import BrandAdvisor
@dataclass
class BridgeState:
    """Shared state across bridge services."""
    advisor:"BrandAdvisor|None"=None
    current_progress:str=""
    current_progress_type:str=""
    matched_skills:list[str]=field(default_factory=list)
    execution_trace:list[dict]=field(default_factory=list)
    thinking_steps:list[dict]=field(default_factory=list)
    update_progress:dict|None=None
    window:object=None
    background_analysis_slug:str|None=None
    _cached_slug:str|None=field(default=None,repr=False)
    _cache_valid:bool=field(default=False,repr=False)
    def get_active_slug(self)->str|None:
        """Get the active brand slug, using cache when available."""
        if not self._cache_valid:
            from sip_videogen.brands.storage import get_active_brand
            self._cached_slug=get_active_brand()
            self._cache_valid=True
        return self._cached_slug
    def set_active_slug(self,slug:str|None)->None:
        """Set the active brand slug, updating both disk and cache."""
        from sip_videogen.brands.storage import set_active_brand
        set_active_brand(slug)
        self._cached_slug=slug
        self._cache_valid=True
    def invalidate_cache(self)->None:
        """Invalidate the cached slug, forcing next get to read from disk."""
        self._cache_valid=False
    def get_brand_dir(self)->"tuple[Path|None,str|None]":
        """Get the active brand directory."""
        from sip_videogen.brands.storage import get_brand_dir
        s=self.get_active_slug()
        if not s:return None,"No brand selected"
        return get_brand_dir(s),None
