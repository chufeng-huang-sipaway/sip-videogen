"""Asset (image) management service."""
from __future__ import annotations

import base64
import io
from pathlib import Path

from sip_videogen.brands.memory import list_brand_assets
from sip_videogen.brands.storage import get_active_brand, get_brand_dir

from ..state import BridgeState
from ..utils.bridge_types import ALLOWED_IMAGE_EXTS, BridgeResponse
from ..utils.path_utils import resolve_assets_path


class AssetService:
    """Asset (image) file operations."""
    def __init__(self,state:BridgeState):self._state=state
    def get_assets(self,slug:str|None=None)->dict:
        """Get asset tree for a brand."""
        try:
            target_slug=slug or get_active_brand()
            if not target_slug:return BridgeResponse(success=False,error="No brand selected").to_dict()
            categories=["logo","packaging","lifestyle","mascot","marketing","generated"]
            tree=[]
            for category in categories:
                assets=list_brand_assets(target_slug,category=category);children=[]
                for asset in assets:
                    filename=asset["filename"];file_path=Path(asset["path"])
                    size=file_path.stat().st_size if file_path.exists()else 0
                    children.append({"name":filename,"type":"image","path":f"{category}/{filename}","size":size})
                tree.append({"name":category,"type":"folder","path":category,"children":children})
            return BridgeResponse(success=True,data={"tree":tree}).to_dict()
        except Exception as e:return BridgeResponse(success=False,error=str(e)).to_dict()
    def get_asset_thumbnail(self,relative_path:str)->dict:
        """Get base64-encoded thumbnail for an asset."""
        try:
            brand_dir,err=self._state.get_brand_dir()
            if err:return BridgeResponse(success=False,error=err).to_dict()
            resolved,error=resolve_assets_path(brand_dir,relative_path)
            if error:return BridgeResponse(success=False,error=error).to_dict()
            if not resolved.exists():return BridgeResponse(success=False,error="Asset not found").to_dict()
            suffix=resolved.suffix.lower()
            if suffix not in ALLOWED_IMAGE_EXTS:return BridgeResponse(success=False,error="Unsupported file type").to_dict()
            if suffix==".svg":
                content=resolved.read_bytes();encoded=base64.b64encode(content).decode("utf-8")
                return BridgeResponse(success=True,data={"dataUrl":f"data:image/svg+xml;base64,{encoded}"}).to_dict()
            from PIL import Image
            with Image.open(resolved)as img:
                img=img.convert("RGBA");img.thumbnail((256,256))
                buf=io.BytesIO();img.save(buf,format="PNG")
                encoded=base64.b64encode(buf.getvalue()).decode("utf-8")
            return BridgeResponse(success=True,data={"dataUrl":f"data:image/png;base64,{encoded}"}).to_dict()
        except Exception as e:return BridgeResponse(success=False,error=str(e)).to_dict()
    def get_asset_full(self,relative_path:str)->dict:
        """Get base64-encoded full-resolution image for an asset."""
        try:
            brand_dir,err=self._state.get_brand_dir()
            if err:return BridgeResponse(success=False,error=err).to_dict()
            resolved,error=resolve_assets_path(brand_dir,relative_path)
            if error:return BridgeResponse(success=False,error=error).to_dict()
            if not resolved.exists():return BridgeResponse(success=False,error="Asset not found").to_dict()
            suffix=resolved.suffix.lower()
            if suffix not in ALLOWED_IMAGE_EXTS:return BridgeResponse(success=False,error="Unsupported file type").to_dict()
            content=resolved.read_bytes();encoded=base64.b64encode(content).decode("utf-8")
            mime_types={".png":"image/png",".jpg":"image/jpeg",".jpeg":"image/jpeg",".gif":"image/gif",".webp":"image/webp",".svg":"image/svg+xml"}
            mime=mime_types.get(suffix,"image/png")
            return BridgeResponse(success=True,data={"dataUrl":f"data:{mime};base64,{encoded}"}).to_dict()
        except Exception as e:return BridgeResponse(success=False,error=str(e)).to_dict()
    def open_asset_in_finder(self,relative_path:str)->dict:
        """Open an asset in Finder."""
        import subprocess
        try:
            brand_dir,err=self._state.get_brand_dir()
            if err:return BridgeResponse(success=False,error=err).to_dict()
            resolved,error=resolve_assets_path(brand_dir,relative_path)
            if error:return BridgeResponse(success=False,error=error).to_dict()
            if not resolved.exists():return BridgeResponse(success=False,error="Asset not found").to_dict()
            if resolved.suffix.lower()not in ALLOWED_IMAGE_EXTS:return BridgeResponse(success=False,error="Unsupported file type").to_dict()
            subprocess.run(["open","-R",str(resolved)],check=True)
            return BridgeResponse(success=True).to_dict()
        except Exception as e:return BridgeResponse(success=False,error=str(e)).to_dict()
    def delete_asset(self,relative_path:str)->dict:
        """Delete an asset file."""
        try:
            brand_dir,err=self._state.get_brand_dir()
            if err:return BridgeResponse(success=False,error=err).to_dict()
            resolved,error=resolve_assets_path(brand_dir,relative_path)
            if error:return BridgeResponse(success=False,error=error).to_dict()
            if not resolved.exists():return BridgeResponse(success=False,error="Asset not found").to_dict()
            if resolved.is_dir():return BridgeResponse(success=False,error="Cannot delete folders").to_dict()
            if resolved.suffix.lower()not in ALLOWED_IMAGE_EXTS:return BridgeResponse(success=False,error="Unsupported file type").to_dict()
            resolved.unlink()
            return BridgeResponse(success=True).to_dict()
        except Exception as e:return BridgeResponse(success=False,error=str(e)).to_dict()
    def rename_asset(self,relative_path:str,new_name:str)->dict:
        """Rename an asset file."""
        try:
            brand_dir,err=self._state.get_brand_dir()
            if err:return BridgeResponse(success=False,error=err).to_dict()
            resolved,error=resolve_assets_path(brand_dir,relative_path)
            if error:return BridgeResponse(success=False,error=error).to_dict()
            if not resolved.exists():return BridgeResponse(success=False,error="Asset not found").to_dict()
            if resolved.suffix.lower()not in ALLOWED_IMAGE_EXTS:return BridgeResponse(success=False,error="Unsupported file type").to_dict()
            if"/"in new_name or"\\"in new_name:return BridgeResponse(success=False,error="Invalid filename").to_dict()
            if Path(new_name).suffix.lower()not in ALLOWED_IMAGE_EXTS:return BridgeResponse(success=False,error="Unsupported file type").to_dict()
            new_path=resolved.parent/new_name
            if new_path.exists():return BridgeResponse(success=False,error=f"File already exists: {new_name}").to_dict()
            resolved.rename(new_path)
            return BridgeResponse(success=True,data={"newPath":f"{resolved.parent.name}/{new_name}"}).to_dict()
        except Exception as e:return BridgeResponse(success=False,error=str(e)).to_dict()
    def upload_asset(self,filename:str,data_base64:str,category:str="generated")->dict:
        """Upload a file to brand's assets directory."""
        try:
            slug=get_active_brand()
            if not slug:return BridgeResponse(success=False,error="No brand selected").to_dict()
            valid_categories=["logo","packaging","lifestyle","mascot","marketing","generated"]
            if category not in valid_categories:return BridgeResponse(success=False,error="Invalid category").to_dict()
            if"/"in filename or"\\"in filename:return BridgeResponse(success=False,error="Invalid filename").to_dict()
            if Path(filename).suffix.lower()not in ALLOWED_IMAGE_EXTS:return BridgeResponse(success=False,error="Unsupported file type").to_dict()
            brand_dir=get_brand_dir(slug);target_dir=brand_dir/"assets"/category
            target_dir.mkdir(parents=True,exist_ok=True)
            target_path=target_dir/filename
            if target_path.exists():return BridgeResponse(success=False,error=f"File already exists: {filename}").to_dict()
            content=base64.b64decode(data_base64);target_path.write_bytes(content)
            return BridgeResponse(success=True,data={"path":f"{category}/{filename}"}).to_dict()
        except Exception as e:return BridgeResponse(success=False,error=str(e)).to_dict()
