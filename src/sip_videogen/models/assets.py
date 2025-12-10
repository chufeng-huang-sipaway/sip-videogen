"""Asset and production models for tracking generated content.

This module defines the data structures for tracking generated images,
video clips, and the overall production package.
"""

from enum import Enum

from pydantic import BaseModel, Field

from sip_videogen.models.script import VideoScript


class AssetType(str, Enum):
    """Type of generated asset."""

    REFERENCE_IMAGE = "reference_image"
    VIDEO_CLIP = "video_clip"


class GeneratedAsset(BaseModel):
    """A generated image or video asset.

    Tracks both local and cloud storage locations for generated assets,
    along with metadata about what the asset represents.
    """

    asset_type: AssetType = Field(description="Type of generated asset")
    element_id: str | None = Field(
        default=None, description="SharedElement ID (for reference images)"
    )
    scene_number: int | None = Field(default=None, description="Scene number (for video clips)")
    local_path: str = Field(description="Local filesystem path to the asset")
    gcs_uri: str | None = Field(default=None, description="GCS URI after upload (gs://bucket/path)")


class ProductionPackage(BaseModel):
    """Complete package for video production.

    Aggregates the script and all generated assets needed to produce
    the final video output.
    """

    script: VideoScript = Field(description="The complete video script")
    reference_images: list[GeneratedAsset] = Field(
        default_factory=list,
        description="Generated reference images for shared elements",
    )
    video_clips: list[GeneratedAsset] = Field(
        default_factory=list, description="Generated video clips for each scene"
    )
    final_video_path: str | None = Field(
        default=None, description="Path to the final concatenated video"
    )

    def get_reference_image_for_element(self, element_id: str) -> GeneratedAsset | None:
        """Find the reference image for a specific shared element.

        Args:
            element_id: The ID of the shared element.

        Returns:
            The GeneratedAsset if found, None otherwise.
        """
        for asset in self.reference_images:
            if asset.element_id == element_id:
                return asset
        return None

    def get_video_clip_for_scene(self, scene_number: int) -> GeneratedAsset | None:
        """Find the video clip for a specific scene.

        Args:
            scene_number: The scene number to look up.

        Returns:
            The GeneratedAsset if found, None otherwise.
        """
        for asset in self.video_clips:
            if asset.scene_number == scene_number:
                return asset
        return None

    @property
    def is_complete(self) -> bool:
        """Check if all assets have been generated.

        Returns:
            True if all reference images and video clips are present.
        """
        # Check reference images for all shared elements
        element_ids = {elem.id for elem in self.script.shared_elements}
        ref_image_ids = {asset.element_id for asset in self.reference_images if asset.element_id}
        if element_ids != ref_image_ids:
            return False

        # Check video clips for all scenes
        scene_numbers = {scene.scene_number for scene in self.script.scenes}
        clip_scene_numbers = {
            asset.scene_number for asset in self.video_clips if asset.scene_number
        }
        if scene_numbers != clip_scene_numbers:
            return False

        return True
