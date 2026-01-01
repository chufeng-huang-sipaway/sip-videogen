"""Aspect ratio model and provider capability definitions.
This module defines canonical aspect ratios for video generation
with provider-specific support tables and fallback logic."""
from __future__ import annotations

import logging
from enum import Enum

logger=logging.getLogger(__name__)
class AspectRatio(str,Enum):
    """Supported aspect ratios for video generation."""
    SQUARE="1:1"
    LANDSCAPE_16_9="16:9"
    PORTRAIT_9_16="9:16"
    CINEMATIC_5_3="5:3"
    PORTRAIT_CINEMATIC_3_5="3:5"
    CLASSIC_4_3="4:3"
    PORTRAIT_CLASSIC_3_4="3:4"
    PHOTO_3_2="3:2"
    PORTRAIT_PHOTO_2_3="2:3"
#Provider-specific supported ratios
PROVIDER_SUPPORTED_RATIOS:dict[str,list[str]]={
"veo":["16:9","9:16"],#VEO: landscape/portrait only
"kling":["1:1","16:9","9:16"],#Kling: standard ratios only
"sora":["16:9","9:16"],#Sora: landscape/portrait only
}
#Sora maps ratios to fixed sizes per resolution
SORA_SIZE_MAP:dict[str,dict[str,str]]={
"16:9":{"720p":"1280x720","1080p":"1792x1024"},
"9:16":{"720p":"720x1280","1080p":"1024x1792"},
}
DEFAULT_ASPECT_RATIO=AspectRatio.SQUARE
def parse_ratio(ratio:str)->tuple[int,int]:
    """Parse ratio string to (width,height) tuple.
    Args:
        ratio: Ratio string like "16:9"
    Returns:
        Tuple of (width,height) as integers
    Raises:
        ValueError: If ratio format is invalid"""
    parts=ratio.split(":")
    if len(parts)!=2:
        raise ValueError(f"Invalid ratio format: {ratio}")
    return int(parts[0]),int(parts[1])
def get_supported_ratio(requested:AspectRatio,provider:str)->tuple[AspectRatio,bool]:
    """Get supported ratio for provider with fallback.
    Args:
        requested: Requested AspectRatio
        provider: Provider name (veo, kling, sora)
    Returns:
        Tuple of (actual_ratio, was_fallback)
    """
    supported=PROVIDER_SUPPORTED_RATIOS.get(provider.lower())
    if supported is None:
        #Unknown provider - assume all ratios supported
        logger.warning(f"Unknown provider '{provider}', assuming all ratios supported")
        return(requested,False)
    if requested.value in supported:
        return(requested,False)
    #Fallback: same orientation first, then 1:1
    try:
        req_w,req_h=parse_ratio(requested.value)
    except ValueError:
        logger.error(f"Cannot parse ratio {requested.value}, falling back to first supported")
        return(AspectRatio(supported[0]),True)
    is_portrait=req_h>req_w
    orientation_fallbacks=["9:16","3:5","2:3","3:4"] if is_portrait else ["16:9","5:3","3:2","4:3"]
    for fallback in orientation_fallbacks:
        if fallback in supported:
            logger.warning(f"Provider {provider} doesn't support {requested.value}, using {fallback}")  # noqa: E501
            return(AspectRatio(fallback),True)
    #Last resort: 1:1 if supported, else first supported
    if "1:1" in supported:
        logger.warning(f"Provider {provider} doesn't support {requested.value}, using 1:1")
        return(AspectRatio.SQUARE,True)
    logger.warning(f"Provider {provider} doesn't support {requested.value}, using {supported[0]}")
    return(AspectRatio(supported[0]),True)
def validate_aspect_ratio(ratio:str|None)->AspectRatio:
    """Validate and convert ratio string to AspectRatio enum.
    Args:
        ratio: Ratio string or None
    Returns:
        Valid AspectRatio enum value (defaults to SQUARE if invalid)"""
    if ratio is None:
        return DEFAULT_ASPECT_RATIO
    try:
        return AspectRatio(ratio)
    except ValueError:
        logger.warning(f"Invalid aspect ratio '{ratio}', defaulting to 1:1")
        return DEFAULT_ASPECT_RATIO
