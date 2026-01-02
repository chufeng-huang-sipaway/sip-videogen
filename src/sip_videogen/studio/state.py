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
    def get_active_slug(self)->str|None:
        """Get the active brand slug from storage."""
        from sip_videogen.brands.storage import get_active_brand
        return get_active_brand()
    def get_brand_dir(self)->"tuple[Path|None,str|None]":
        """Get the active brand directory."""
        from sip_videogen.brands.storage import get_brand_dir
        s=self.get_active_slug()
        if not s:return None,"No brand selected"
        return get_brand_dir(s),None
