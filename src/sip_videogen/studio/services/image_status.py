"""Image status tracking service for workstation curation."""
from __future__ import annotations
import json
import os
import uuid
from datetime import datetime,timezone
from pathlib import Path
from typing import Literal
from sip_videogen.brands.storage import get_brand_dir
from ..state import BridgeState
from ..utils.bridge_types import bridge_ok,bridge_error
ImageStatus=Literal["unsorted"]
STATUS_FILE_NAME="image_status.json"
CURRENT_VERSION=1
class ImageStatusService:
    """Track image lifecycle with viewedAt for unread/read status."""
    def __init__(self,state:BridgeState):self._state=state
    def _get_status_file(self,brand_slug:str)->Path:
        """Get path to image_status.json for a brand."""
        return get_brand_dir(brand_slug)/STATUS_FILE_NAME
    def _load_status_data(self,brand_slug:str)->dict:
        """Load status data from file, creating empty structure if missing."""
        fp=self._get_status_file(brand_slug)
        if not fp.exists():return {"version":CURRENT_VERSION,"images":{}}
        try:
            with open(fp,"r",encoding="utf-8")as f:return json.load(f)
        except(json.JSONDecodeError,OSError):return {"version":CURRENT_VERSION,"images":{}}
    def _save_status_data(self,brand_slug:str,data:dict)->None:
        """Atomically save status data to file."""
        fp=self._get_status_file(brand_slug);tmp=fp.with_suffix(".json.tmp")
        fp.parent.mkdir(parents=True,exist_ok=True)
        with open(tmp,"w",encoding="utf-8")as f:json.dump(data,f,indent=2)
        os.replace(tmp,fp)
    def _generate_id(self)->str:
        """Generate unique image ID."""
        return f"img_{uuid.uuid4().hex[:12]}"
    def _now_iso(self)->str:
        """Get current time as ISO 8601 string."""
        return datetime.now(timezone.utc).isoformat()
    def get_status(self,brand_slug:str,image_id:str)->dict:
        """Get status entry for a specific image."""
        try:
            data=self._load_status_data(brand_slug);images=data.get("images",{})
            if image_id not in images:return bridge_error(f"Image not found: {image_id}")
            return bridge_ok(images[image_id])
        except Exception as e:return bridge_error(str(e))
    def set_status(self,brand_slug:str,image_id:str,status:ImageStatus)->dict:
        """Update status of an image."""
        try:
            data=self._load_status_data(brand_slug);images=data.get("images",{})
            if image_id not in images:return bridge_error(f"Image not found: {image_id}")
            entry=images[image_id];entry["status"]=status
            images[image_id]=entry;data["images"]=images;self._save_status_data(brand_slug,data)
            return bridge_ok(entry)
        except Exception as e:return bridge_error(str(e))
    def list_by_status(self,brand_slug:str,status:ImageStatus)->dict:
        """List all images with a specific status."""
        try:
            data=self._load_status_data(brand_slug);images=data.get("images",{})
            filtered=[v for v in images.values()if v.get("status")==status]
            return bridge_ok(filtered)
        except Exception as e:return bridge_error(str(e))
    def register_image(self,brand_slug:str,image_path:str,prompt:str|None=None,source_template_path:str|None=None)->dict:
        """Register a new image with unsorted status."""
        try:
            data=self._load_status_data(brand_slug);image_id=self._generate_id();now=self._now_iso()
            source_path=source_template_path
            if source_template_path and not source_template_path.startswith(("data:","http://","https://")):
                p=Path(source_template_path)
                if not p.is_absolute():
                    brand_dir=get_brand_dir(brand_slug)
                    resolved=(brand_dir/source_template_path).resolve()
                    try:
                        resolved.relative_to(brand_dir.resolve())
                        source_path=str(resolved)
                    except ValueError:
                        source_path=source_template_path
                else:
                    source_path=str(p)
            entry={"id":image_id,"status":"unsorted","originalPath":image_path,"currentPath":image_path,"prompt":prompt,"sourceTemplatePath":source_path,"timestamp":now,"viewedAt":None}
            data["images"][image_id]=entry;self._save_status_data(brand_slug,data)
            return bridge_ok(entry)
        except Exception as e:return bridge_error(str(e))
    def mark_viewed(self,brand_slug:str,image_id:str)->dict:
        """Mark image as viewed (read)."""
        try:
            data=self._load_status_data(brand_slug);images=data.get("images",{})
            if image_id not in images:return bridge_error(f"Image not found: {image_id}")
            entry=images[image_id]
            if entry.get("viewedAt")is None:entry["viewedAt"]=self._now_iso();images[image_id]=entry;data["images"]=images;self._save_status_data(brand_slug,data)
            return bridge_ok(entry)
        except Exception as e:return bridge_error(str(e))
    def update_path(self,brand_slug:str,image_id:str,new_path:str)->dict:
        """Update the current path of an image."""
        try:
            data=self._load_status_data(brand_slug);images=data.get("images",{})
            if image_id not in images:return bridge_error(f"Image not found: {image_id}")
            images[image_id]["currentPath"]=new_path;data["images"]=images
            self._save_status_data(brand_slug,data)
            return bridge_ok(images[image_id])
        except Exception as e:return bridge_error(str(e))
    def delete_image(self,brand_slug:str,image_id:str)->dict:
        """Remove an image entry from the status file."""
        try:
            data=self._load_status_data(brand_slug);images=data.get("images",{})
            if image_id not in images:return bridge_error(f"Image not found: {image_id}")
            del images[image_id];data["images"]=images;self._save_status_data(brand_slug,data)
            return bridge_ok()
        except Exception as e:return bridge_error(str(e))
    def find_by_path(self,brand_slug:str,path:str)->dict:
        """Find image entry by current path. Returns entry with ID or error if not found."""
        try:
            data=self._load_status_data(brand_slug);images=data.get("images",{})
            for img_id,entry in images.items():
                if entry.get("currentPath")==path or entry.get("originalPath")==path:
                    return bridge_ok({**entry,"id":img_id})
            return bridge_error(f"Image not found for path: {path}")
        except Exception as e:return bridge_error(str(e))
    def register_or_find(self,brand_slug:str,path:str,status:ImageStatus="unsorted")->dict:
        """Find existing entry by path or register new one."""
        try:
            found=self.find_by_path(brand_slug,path)
            if found.get("success"):return found
            #Register new entry
            data=self._load_status_data(brand_slug);image_id=self._generate_id();now=self._now_iso()
            entry={"id":image_id,"status":status,"originalPath":path,"currentPath":path,"prompt":None,"sourceTemplatePath":None,"timestamp":now,"viewedAt":None}
            data["images"][image_id]=entry;self._save_status_data(brand_slug,data)
            return bridge_ok(entry)
        except Exception as e:return bridge_error(str(e))
    def backfill_from_folders(self,brand_slug:str)->dict:
        """Scan asset folders and backfill missing entries."""
        try:
            from sip_videogen.studio.utils.bridge_types import ALLOWED_IMAGE_EXTS
            brand_dir=get_brand_dir(brand_slug);data=self._load_status_data(brand_slug)
            existing_paths={e.get("currentPath")for e in data.get("images",{}).values()}
            added=[]
            folder_path=brand_dir/"assets"/"generated"
            if folder_path.exists():
                for fp in folder_path.iterdir():
                    if not fp.is_file()or fp.suffix.lower()not in ALLOWED_IMAGE_EXTS:continue
                    path_str=str(fp)
                    if path_str in existing_paths:continue
                    image_id=self._generate_id();now=self._now_iso()
                    entry={"id":image_id,"status":"unsorted","originalPath":path_str,"currentPath":path_str,"prompt":None,"sourceTemplatePath":None,"timestamp":now,"viewedAt":None}
                    data["images"][image_id]=entry;added.append(entry)
            if added:self._save_status_data(brand_slug,data)
            return bridge_ok({"added":added,"count":len(added)})
        except Exception as e:return bridge_error(str(e))
