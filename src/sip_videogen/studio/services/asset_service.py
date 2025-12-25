"""Asset (image/video) management service."""
from __future__ import annotations

import base64
import io
from pathlib import Path

from sip_videogen.brands.memory import list_brand_assets
from sip_videogen.brands.storage import get_active_brand, get_brand_dir

from ..state import BridgeState
from ..utils.bridge_types import ALLOWED_IMAGE_EXTS,ALLOWED_VIDEO_EXTS,ASSET_CATEGORIES,MIME_TYPES,VIDEO_MIME_TYPES,bridge_ok,bridge_error
from ..utils.os_utils import reveal_in_file_manager
from ..utils.path_utils import resolve_assets_path,resolve_in_dir


class AssetService:
    """Asset (image/video) file operations."""
    def __init__(self,state:BridgeState):self._state=state
    def _resolve_image_path(self,image_path:str)->tuple[Path|None,str|None]:
        """Resolve an image path within the active brand directory."""
        brand_dir,err=self._state.get_brand_dir()
        if err:return None,err
        path=Path(image_path)
        if path.is_absolute():
            resolved=path.resolve()
        else:
            resolved,error=resolve_in_dir(brand_dir,image_path)
            if error:return None,error
        try:resolved.relative_to(brand_dir.resolve())
        except ValueError:return None,"Invalid path: outside brand directory"
        return resolved,None
    def get_assets(self,slug:str|None=None)->dict:
        """Get asset tree for a brand."""
        try:
            target_slug=slug or get_active_brand()
            if not target_slug:return bridge_error("No brand selected")
            tree=[]
            for category in ASSET_CATEGORIES:
                assets=list_brand_assets(target_slug,category=category);children=[]
                for asset in assets:
                    filename=asset["filename"];fp=Path(asset["path"])
                    size=fp.stat().st_size if fp.exists()else 0
                    asset_type=asset.get("type","image")
                    children.append({"name":filename,"type":asset_type,"path":f"{category}/{filename}","size":size})
                tree.append({"name":category,"type":"folder","path":category,"children":children})
            return bridge_ok({"tree":tree})
        except Exception as e:return bridge_error(str(e))
    def get_asset_thumbnail(self,relative_path:str)->dict:
        """Get base64-encoded thumbnail for an asset."""
        try:
            brand_dir,err=self._state.get_brand_dir()
            if err:return bridge_error(err)
            resolved,error=resolve_assets_path(brand_dir,relative_path)
            if error:return bridge_error(error)
            if not resolved.exists():return bridge_error("Asset not found")
            suffix=resolved.suffix.lower()
            if suffix not in ALLOWED_IMAGE_EXTS:return bridge_error("Unsupported file type")
            if suffix==".svg":
                content=resolved.read_bytes();enc=base64.b64encode(content).decode("utf-8")
                return bridge_ok({"dataUrl":f"data:image/svg+xml;base64,{enc}"})
            from PIL import Image
            with Image.open(resolved)as img:
                img=img.convert("RGBA");img.thumbnail((256,256))
                buf=io.BytesIO();img.save(buf,format="PNG")
                enc=base64.b64encode(buf.getvalue()).decode("utf-8")
            return bridge_ok({"dataUrl":f"data:image/png;base64,{enc}"})
        except Exception as e:return bridge_error(str(e))
    def get_asset_full(self,relative_path:str)->dict:
        """Get base64-encoded full-resolution image for an asset."""
        try:
            brand_dir,err=self._state.get_brand_dir()
            if err:return bridge_error(err)
            resolved,error=resolve_assets_path(brand_dir,relative_path)
            if error:return bridge_error(error)
            if not resolved.exists():return bridge_error("Asset not found")
            suffix=resolved.suffix.lower()
            if suffix not in ALLOWED_IMAGE_EXTS:return bridge_error("Unsupported file type")
            content=resolved.read_bytes();enc=base64.b64encode(content).decode("utf-8")
            mime=MIME_TYPES.get(suffix,"image/png")
            return bridge_ok({"dataUrl":f"data:{mime};base64,{enc}"})
        except Exception as e:return bridge_error(str(e))
    def get_image_data(self,image_path:str)->dict:
        """Get base64-encoded image data for a file under the brand directory."""
        try:
            resolved,error=self._resolve_image_path(image_path)
            if error:return bridge_error(error)
            if not resolved.exists():return bridge_error("Image not found")
            suffix=resolved.suffix.lower()
            if suffix not in ALLOWED_IMAGE_EXTS:return bridge_error("Unsupported file type")
            content=resolved.read_bytes();enc=base64.b64encode(content).decode("utf-8")
            mime="image/svg+xml"if suffix==".svg"else MIME_TYPES.get(suffix,"image/png")
            return bridge_ok({"dataUrl":f"data:{mime};base64,{enc}"})
        except Exception as e:return bridge_error(str(e))
    def get_image_thumbnail(self,image_path:str)->dict:
        """Get base64-encoded thumbnail for a file under the brand directory."""
        try:
            resolved,error=self._resolve_image_path(image_path)
            if error:return bridge_error(error)
            if not resolved.exists():return bridge_error("Image not found")
            suffix=resolved.suffix.lower()
            if suffix not in ALLOWED_IMAGE_EXTS:return bridge_error("Unsupported file type")
            if suffix==".svg":
                content=resolved.read_bytes();enc=base64.b64encode(content).decode("utf-8")
                return bridge_ok({"dataUrl":f"data:image/svg+xml;base64,{enc}"})
            from PIL import Image
            with Image.open(resolved)as img:
                img=img.convert("RGBA");img.thumbnail((256,256))
                buf=io.BytesIO();img.save(buf,format="PNG")
                enc=base64.b64encode(buf.getvalue()).decode("utf-8")
            return bridge_ok({"dataUrl":f"data:image/png;base64,{enc}"})
        except Exception as e:return bridge_error(str(e))
    def open_asset_in_finder(self,relative_path:str)->dict:
        """Open an asset in Finder."""
        try:
            brand_dir,err=self._state.get_brand_dir()
            if err:return bridge_error(err)
            resolved,error=resolve_assets_path(brand_dir,relative_path)
            if error:return bridge_error(error)
            if not resolved.exists():return bridge_error("Asset not found")
            if resolved.suffix.lower()not in(ALLOWED_IMAGE_EXTS|ALLOWED_VIDEO_EXTS):return bridge_error("Unsupported file type")
            reveal_in_file_manager(resolved)
            return bridge_ok()
        except Exception as e:return bridge_error(str(e))
    def delete_asset(self,relative_path:str)->dict:
        """Delete an asset file."""
        try:
            brand_dir,err=self._state.get_brand_dir()
            if err:return bridge_error(err)
            resolved,error=resolve_assets_path(brand_dir,relative_path)
            if error:return bridge_error(error)
            if not resolved.exists():return bridge_error("Asset not found")
            if resolved.is_dir():return bridge_error("Cannot delete folders")
            if resolved.suffix.lower()not in(ALLOWED_IMAGE_EXTS|ALLOWED_VIDEO_EXTS):return bridge_error("Unsupported file type")
            resolved.unlink()
            return bridge_ok()
        except Exception as e:return bridge_error(str(e))
    def rename_asset(self,relative_path:str,new_name:str)->dict:
        """Rename an asset file."""
        try:
            brand_dir,err=self._state.get_brand_dir()
            if err:return bridge_error(err)
            resolved,error=resolve_assets_path(brand_dir,relative_path)
            if error:return bridge_error(error)
            if not resolved.exists():return bridge_error("Asset not found")
            if resolved.suffix.lower()not in(ALLOWED_IMAGE_EXTS|ALLOWED_VIDEO_EXTS):return bridge_error("Unsupported file type")
            if"/"in new_name or"\\"in new_name:return bridge_error("Invalid filename")
            if Path(new_name).suffix.lower()not in(ALLOWED_IMAGE_EXTS|ALLOWED_VIDEO_EXTS):return bridge_error("Unsupported file type")
            new_path=resolved.parent/new_name
            if new_path.exists():return bridge_error(f"File already exists: {new_name}")
            resolved.rename(new_path)
            return bridge_ok({"newPath":f"{resolved.parent.name}/{new_name}"})
        except Exception as e:return bridge_error(str(e))
    def upload_asset(self,filename:str,data_base64:str,category:str="generated")->dict:
        """Upload a file to brand's assets directory."""
        try:
            slug=get_active_brand()
            if not slug:return bridge_error("No brand selected")
            if category not in ASSET_CATEGORIES:return bridge_error("Invalid category")
            if"/"in filename or"\\"in filename:return bridge_error("Invalid filename")
            if Path(filename).suffix.lower()not in ALLOWED_IMAGE_EXTS:return bridge_error("Unsupported file type")
            brand_dir=get_brand_dir(slug);target_dir=brand_dir/"assets"/category
            target_dir.mkdir(parents=True,exist_ok=True)
            target_path=target_dir/filename
            if target_path.exists():return bridge_error(f"File already exists: {filename}")
            content=base64.b64decode(data_base64);target_path.write_bytes(content)
            return bridge_ok({"path":f"{category}/{filename}"})
        except Exception as e:return bridge_error(str(e))
    def get_video_data(self,relative_path:str)->dict:
        """Get base64-encoded video data.

        Args:
            relative_path: Path relative to brand assets (e.g., "video/scene_001.mp4")

        Returns:
            dict with dataUrl containing base64-encoded video data
        """
        try:
            brand_dir,err=self._state.get_brand_dir()
            if err:return bridge_error(err)
            resolved,error=resolve_assets_path(brand_dir,relative_path)
            if error:return bridge_error(error)
            if not resolved.exists():return bridge_error("Video not found")
            suffix=resolved.suffix.lower()
            if suffix not in ALLOWED_VIDEO_EXTS:return bridge_error("Unsupported video type")
            content=resolved.read_bytes();enc=base64.b64encode(content).decode("utf-8")
            mime=VIDEO_MIME_TYPES.get(suffix,"video/mp4")
            return bridge_ok({"dataUrl":f"data:{mime};base64,{enc}","path":str(resolved),"filename":resolved.name})
        except Exception as e:return bridge_error(str(e))
    def get_video_path(self,relative_path:str)->dict:
        """Get the absolute file path for a video (for local playback).

        Args:
            relative_path: Path relative to brand assets (e.g., "video/scene_001.mp4")

        Returns:
            dict with absolute path to the video file
        """
        try:
            brand_dir,err=self._state.get_brand_dir()
            if err:return bridge_error(err)
            resolved,error=resolve_assets_path(brand_dir,relative_path)
            if error:return bridge_error(error)
            if not resolved.exists():return bridge_error("Video not found")
            suffix=resolved.suffix.lower()
            if suffix not in ALLOWED_VIDEO_EXTS:return bridge_error("Unsupported video type")
            return bridge_ok({"path":str(resolved),"filename":resolved.name,"file_url":resolved.resolve().as_uri()})
        except Exception as e:return bridge_error(str(e))
