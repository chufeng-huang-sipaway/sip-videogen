"""Centralized constants for sip-videogen."""

# Asset categories used across Brand Studio
ASSET_CATEGORIES = ["logo", "packaging", "lifestyle", "mascot", "marketing", "generated", "video"]
# Allowed file extensions
ALLOWED_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}
ALLOWED_VIDEO_EXTS = {".mp4", ".mov", ".webm"}
ALLOWED_TEXT_EXTS = {".md", ".txt", ".json", ".yaml", ".yml"}
# MIME type mappings for images
MIME_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".svg": "image/svg+xml",
}
# MIME type mappings for videos
VIDEO_MIME_TYPES = {".mp4": "video/mp4", ".mov": "video/quicktime", ".webm": "video/webm"}
