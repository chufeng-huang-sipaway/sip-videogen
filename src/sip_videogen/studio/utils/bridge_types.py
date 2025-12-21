"""Shared types and constants for bridge layer."""
from dataclasses import asdict,dataclass
from typing import Any
ALLOWED_IMAGE_EXTS={".png",".jpg",".jpeg",".gif",".webp",".svg"}
ALLOWED_TEXT_EXTS={".md",".txt",".json",".yaml",".yml"}
@dataclass
class BridgeResponse:
    """Standard response format for bridge methods."""
    success:bool
    data:Any=None
    error:str|None=None
    def to_dict(self)->dict:return asdict(self)
