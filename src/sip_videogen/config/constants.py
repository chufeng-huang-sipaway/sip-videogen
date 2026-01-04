"""Centralized constants for sip-videogen."""
#Resolution mappings (from aspect_ratio.py, sora_generator.py)
RESOLUTIONS={"16:9":{"720p":"1280x720","1080p":"1792x1024"},"9:16":{"720p":"720x1280","1080p":"1024x1792"}}
#API timeouts in seconds
class Timeouts:
    KLING_API=60.0
    MUSIC_GENERATION=120
    UPDATE_CHECK=30.0
    UPDATE_DOWNLOAD=600.0
#Generation limits
class Limits:
    MAX_TOKENS_FULL=8000
    MAX_TOKENS_COMPACT=4000
    MAX_PRODUCTS=50
    CHUNK_SIZE_DOWNLOAD=65536
    CHUNK_SIZE_FILE_MIN=100
    CHUNK_SIZE_FILE_MAX=10000
