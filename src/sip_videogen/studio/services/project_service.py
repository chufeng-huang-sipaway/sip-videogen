"""Project management service."""
from __future__ import annotations
import re
from datetime import datetime
from sip_videogen.brands.models import ProjectFull,ProjectStatus
from sip_videogen.brands.storage import(count_project_assets,create_project,delete_project,get_active_project,list_project_assets,list_projects,load_project,save_project,set_active_project)
from ..state import BridgeState
from ..utils.bridge_types import BridgeResponse
class ProjectService:
    """Project CRUD and asset listing."""
    def __init__(self,state:BridgeState):self._state=state
    def get_projects(self,brand_slug:str|None=None)->dict:
        """Get list of projects for a brand."""
        try:
            target_slug=brand_slug or self._state.get_active_slug()
            if not target_slug:return BridgeResponse(success=False,error="No brand selected").to_dict()
            projects=list_projects(target_slug);active=get_active_project(target_slug)
            return BridgeResponse(success=True,data={"projects":[{"slug":p.slug,"name":p.name,"status":p.status.value,"asset_count":count_project_assets(target_slug,p.slug),"created_at":p.created_at.isoformat(),"updated_at":p.updated_at.isoformat()}for p in projects],"active_project":active}).to_dict()
        except Exception as e:return BridgeResponse(success=False,error=str(e)).to_dict()
    def get_project(self,project_slug:str)->dict:
        """Get detailed project information."""
        try:
            slug=self._state.get_active_slug()
            if not slug:return BridgeResponse(success=False,error="No brand selected").to_dict()
            project=load_project(slug,project_slug)
            if not project:return BridgeResponse(success=False,error=f"Project '{project_slug}' not found").to_dict()
            assets=list_project_assets(slug,project_slug)
            return BridgeResponse(success=True,data={"slug":project.slug,"name":project.name,"status":project.status.value,"instructions":project.instructions,"assets":assets,"asset_count":len(assets),"created_at":project.created_at.isoformat(),"updated_at":project.updated_at.isoformat()}).to_dict()
        except Exception as e:return BridgeResponse(success=False,error=str(e)).to_dict()
    def create_project(self,name:str,instructions:str="")->dict:
        """Create a new project."""
        try:
            slug=self._state.get_active_slug()
            if not slug:return BridgeResponse(success=False,error="No brand selected").to_dict()
            if not name.strip():return BridgeResponse(success=False,error="Project name is required").to_dict()
            project_slug=re.sub(r"[^a-z0-9]+","-",name.lower()).strip("-")
            if not project_slug:return BridgeResponse(success=False,error="Invalid project name").to_dict()
            if load_project(slug,project_slug):return BridgeResponse(success=False,error=f"Project '{project_slug}' already exists").to_dict()
            now=datetime.utcnow()
            project=ProjectFull(slug=project_slug,name=name.strip(),status=ProjectStatus.ACTIVE,instructions=instructions.strip(),created_at=now,updated_at=now)
            create_project(slug,project)
            return BridgeResponse(success=True,data={"slug":project_slug}).to_dict()
        except Exception as e:return BridgeResponse(success=False,error=str(e)).to_dict()
    def update_project(self,project_slug:str,name:str|None=None,instructions:str|None=None,status:str|None=None)->dict:
        """Update an existing project."""
        try:
            slug=self._state.get_active_slug()
            if not slug:return BridgeResponse(success=False,error="No brand selected").to_dict()
            project=load_project(slug,project_slug)
            if not project:return BridgeResponse(success=False,error=f"Project '{project_slug}' not found").to_dict()
            if name is not None:project.name=name.strip()
            if instructions is not None:project.instructions=instructions.strip()
            if status is not None:
                if status=="active":project.status=ProjectStatus.ACTIVE
                elif status=="archived":project.status=ProjectStatus.ARCHIVED
                else:return BridgeResponse(success=False,error=f"Invalid status: {status}").to_dict()
            project.updated_at=datetime.utcnow();save_project(slug,project)
            return BridgeResponse(success=True,data={"slug":project.slug,"name":project.name,"status":project.status.value}).to_dict()
        except Exception as e:return BridgeResponse(success=False,error=str(e)).to_dict()
    def delete_project(self,project_slug:str)->dict:
        """Delete a project."""
        try:
            slug=self._state.get_active_slug()
            if not slug:return BridgeResponse(success=False,error="No brand selected").to_dict()
            active=get_active_project(slug)
            if active==project_slug:set_active_project(slug,None)
            deleted=delete_project(slug,project_slug)
            if not deleted:return BridgeResponse(success=False,error=f"Project '{project_slug}' not found").to_dict()
            return BridgeResponse(success=True).to_dict()
        except Exception as e:return BridgeResponse(success=False,error=str(e)).to_dict()
    def set_active_project(self,project_slug:str|None)->dict:
        """Set the active project for the current brand."""
        try:
            slug=self._state.get_active_slug()
            if not slug:return BridgeResponse(success=False,error="No brand selected").to_dict()
            if project_slug is not None:
                project=load_project(slug,project_slug)
                if not project:return BridgeResponse(success=False,error=f"Project '{project_slug}' not found").to_dict()
            set_active_project(slug,project_slug)
            return BridgeResponse(success=True,data={"active_project":project_slug}).to_dict()
        except Exception as e:return BridgeResponse(success=False,error=str(e)).to_dict()
    def get_active_project(self)->dict:
        """Get the active project for the current brand."""
        try:
            slug=self._state.get_active_slug()
            if not slug:return BridgeResponse(success=False,error="No brand selected").to_dict()
            active=get_active_project(slug)
            return BridgeResponse(success=True,data={"active_project":active}).to_dict()
        except Exception as e:return BridgeResponse(success=False,error=str(e)).to_dict()
    def get_project_assets(self,project_slug:str)->dict:
        """Get list of generated assets for a project."""
        try:
            slug=self._state.get_active_slug()
            if not slug:return BridgeResponse(success=False,error="No brand selected").to_dict()
            assets=list_project_assets(slug,project_slug)
            return BridgeResponse(success=True,data={"assets":assets}).to_dict()
        except Exception as e:return BridgeResponse(success=False,error=str(e)).to_dict()
    def get_general_assets(self,brand_slug:str|None=None)->dict:
        """Get assets not belonging to any project (no project prefix)."""
        from pathlib import Path
        from sip_videogen.brands.storage import get_brand_dir
        try:
            slug=brand_slug or self._state.get_active_slug()
            if not slug:return BridgeResponse(success=False,error="No brand selected").to_dict()
            brand_dir=get_brand_dir(slug);assets=[]
            projects=[p.slug for p in list_projects(slug)]
            for folder in["generated","video"]:
                folder_path=brand_dir/"assets"/folder
                if not folder_path.exists():continue
                for f in folder_path.iterdir():
                    if not f.is_file():continue
                    name=f.name;has_project=False
                    for p in projects:
                        if name.startswith(f"{p}__"):has_project=True;break
                    if not has_project:assets.append(f"{folder}/{name}")
            return BridgeResponse(success=True,data={"assets":sorted(assets),"count":len(assets)}).to_dict()
        except Exception as e:return BridgeResponse(success=False,error=str(e)).to_dict()
