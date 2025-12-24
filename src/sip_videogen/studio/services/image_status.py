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
ImageStatus=Literal["unsorted","kept","trashed"]
STATUS_FILE_NAME="image_status.json"
CURRENT_VERSION=1
class ImageStatusService:
    """Track image lifecycle status (unsorted → kept/trashed)."""
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
            entry=images[image_id];entry["status"]=status;now=self._now_iso()
            if status=="kept":entry["keptAt"]=now;entry["trashedAt"]=None
            elif status=="trashed":entry["trashedAt"]=now;entry["keptAt"]=None
            else:entry["keptAt"]=None;entry["trashedAt"]=None
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
            entry={"id":image_id,"status":"unsorted","originalPath":image_path,"currentPath":image_path,"prompt":prompt,"sourceTemplatePath":source_template_path,"timestamp":now,"keptAt":None,"trashedAt":None}
            data["images"][image_id]=entry;self._save_status_data(brand_slug,data)
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
    def backfill_from_folders(self,brand_slug:str)->dict:
        """Scan asset folders and backfill missing entries."""
        try:
            from sip_videogen.studio.utils.bridge_types import ALLOWED_IMAGE_EXTS
            brand_dir=get_brand_dir(brand_slug);data=self._load_status_data(brand_slug)
            existing_paths={e.get("currentPath")for e in data.get("images",{}).values()}
            folders_status=[("generated","unsorted"),("kept","kept"),("trash","trashed")]
            added=[]
            for folder,status in folders_status:
                folder_path=brand_dir/"assets"/folder
                if not folder_path.exists():continue
                for fp in folder_path.iterdir():
                    if not fp.is_file()or fp.suffix.lower()not in ALLOWED_IMAGE_EXTS:continue
                    path_str=str(fp)
                    if path_str in existing_paths:continue
                    image_id=self._generate_id();now=self._now_iso()
                    entry={"id":image_id,"status":status,"originalPath":path_str,"currentPath":path_str,"prompt":None,"sourceTemplatePath":None,"timestamp":now,"keptAt":now if status=="kept"else None,"trashedAt":now if status=="trashed"else None}
                    data["images"][image_id]=entry;added.append(entry)
            if added:self._save_status_data(brand_slug,data)
            return bridge_ok({"added":added,"count":len(added)})
        except Exception as e:return bridge_error(str(e))
    def cleanup_old_trash(self,brand_slug:str,days:int=30)->dict:
        """Delete trash items older than specified days."""
        try:
            from datetime import timedelta
            data=self._load_status_data(brand_slug);images=data.get("images",{})
            cutoff=datetime.now(timezone.utc)-timedelta(days=days);deleted=[]
            to_remove=[]
            for image_id,entry in images.items():
                if entry.get("status")!="trashed":continue
                trashed_at=entry.get("trashedAt")
                if not trashed_at:continue
                try:trash_dt=datetime.fromisoformat(trashed_at)
                except ValueError:continue
                if trash_dt<cutoff:
                    path=Path(entry.get("currentPath",""))
                    if path.exists():
                        try:path.unlink()
                        except OSError:pass
                    to_remove.append(image_id);deleted.append(entry)
            for image_id in to_remove:del images[image_id]
            if to_remove:data["images"]=images;self._save_status_data(brand_slug,data)
            return bridge_ok({"deleted":deleted,"count":len(deleted)})
        except Exception as e:return bridge_error(str(e))
