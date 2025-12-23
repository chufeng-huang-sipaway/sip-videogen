"""Template management service."""
from __future__ import annotations
import base64,io,re
from datetime import datetime
from pathlib import Path
from sip_videogen.brands.models import TemplateFull
from sip_videogen.brands.storage import(add_template_image,create_template,delete_template,delete_template_image,list_template_images,list_templates,load_template,save_template,set_primary_template_image)
from ..state import BridgeState
from ..utils.bridge_types import ALLOWED_IMAGE_EXTS,BridgeResponse
from ..utils.path_utils import resolve_in_dir
class TemplateService:
    """Template CRUD and image operations."""
    def __init__(self,state:BridgeState):self._state=state
    def get_templates(self,brand_slug:str|None=None)->dict:
        """Get list of templates for a brand."""
        try:
            target_slug=brand_slug or self._state.get_active_slug()
            if not target_slug:return BridgeResponse(success=False,error="No brand selected").to_dict()
            templates=list_templates(target_slug)
            return BridgeResponse(success=True,data={"templates":[{"slug":t.slug,"name":t.name,"description":t.description,"primary_image":t.primary_image,"default_strict":t.default_strict,"created_at":t.created_at.isoformat(),"updated_at":t.updated_at.isoformat()}for t in templates]}).to_dict()
        except Exception as e:return BridgeResponse(success=False,error=str(e)).to_dict()
    def get_template(self,template_slug:str)->dict:
        """Get detailed template information."""
        try:
            slug=self._state.get_active_slug()
            if not slug:return BridgeResponse(success=False,error="No brand selected").to_dict()
            template=load_template(slug,template_slug)
            if not template:return BridgeResponse(success=False,error=f"Template '{template_slug}' not found").to_dict()
            analysis_data=None
            if template.analysis:analysis_data=template.analysis.model_dump()
            return BridgeResponse(success=True,data={"slug":template.slug,"name":template.name,"description":template.description,"images":template.images,"primary_image":template.primary_image,"default_strict":template.default_strict,"analysis":analysis_data,"created_at":template.created_at.isoformat(),"updated_at":template.updated_at.isoformat()}).to_dict()
        except Exception as e:return BridgeResponse(success=False,error=str(e)).to_dict()
    def create_template(self,name:str,description:str,images:list[dict]|None=None,default_strict:bool=True)->dict:
        """Create a new template."""
        try:
            slug=self._state.get_active_slug()
            if not slug:return BridgeResponse(success=False,error="No brand selected").to_dict()
            if not name.strip():return BridgeResponse(success=False,error="Template name is required").to_dict()
            template_slug=re.sub(r"[^a-z0-9]+","-",name.lower()).strip("-")
            if not template_slug:return BridgeResponse(success=False,error="Invalid template name").to_dict()
            if load_template(slug,template_slug):return BridgeResponse(success=False,error=f"Template '{template_slug}' already exists").to_dict()
            now=datetime.utcnow()
            template=TemplateFull(slug=template_slug,name=name.strip(),description=description.strip(),images=[],primary_image="",default_strict=default_strict,analysis=None,created_at=now,updated_at=now)
            create_template(slug,template)
            if images:
                for img in images:
                    filename=img.get("filename","");data_b64=img.get("data","")
                    if not filename or not data_b64:continue
                    ext=Path(filename).suffix.lower()
                    if ext not in ALLOWED_IMAGE_EXTS:continue
                    try:content=base64.b64decode(data_b64);add_template_image(slug,template_slug,filename,content)
                    except Exception:pass
            return BridgeResponse(success=True,data={"slug":template_slug}).to_dict()
        except Exception as e:return BridgeResponse(success=False,error=str(e)).to_dict()
    def update_template(self,template_slug:str,name:str|None=None,description:str|None=None,default_strict:bool|None=None)->dict:
        """Update an existing template."""
        try:
            slug=self._state.get_active_slug()
            if not slug:return BridgeResponse(success=False,error="No brand selected").to_dict()
            template=load_template(slug,template_slug)
            if not template:return BridgeResponse(success=False,error=f"Template '{template_slug}' not found").to_dict()
            if name is not None:template.name=name.strip()
            if description is not None:template.description=description.strip()
            if default_strict is not None:template.default_strict=default_strict
            template.updated_at=datetime.utcnow();save_template(slug,template)
            return BridgeResponse(success=True,data={"slug":template.slug,"name":template.name,"description":template.description,"default_strict":template.default_strict}).to_dict()
        except Exception as e:return BridgeResponse(success=False,error=str(e)).to_dict()
    def reanalyze_template(self,template_slug:str)->dict:
        """Re-run Gemini analysis on template (placeholder - analyzer not yet implemented)."""
        try:
            slug=self._state.get_active_slug()
            if not slug:return BridgeResponse(success=False,error="No brand selected").to_dict()
            template=load_template(slug,template_slug)
            if not template:return BridgeResponse(success=False,error=f"Template '{template_slug}' not found").to_dict()
            #TODO: Call template analyzer when implemented in Phase 1
            return BridgeResponse(success=False,error="Template analyzer not yet implemented").to_dict()
        except Exception as e:return BridgeResponse(success=False,error=str(e)).to_dict()
    def delete_template(self,template_slug:str)->dict:
        """Delete a template and all its files."""
        try:
            slug=self._state.get_active_slug()
            if not slug:return BridgeResponse(success=False,error="No brand selected").to_dict()
            deleted=delete_template(slug,template_slug)
            if not deleted:return BridgeResponse(success=False,error=f"Template '{template_slug}' not found").to_dict()
            return BridgeResponse(success=True).to_dict()
        except Exception as e:return BridgeResponse(success=False,error=str(e)).to_dict()
    def get_template_images(self,template_slug:str)->dict:
        """Get list of images for a template."""
        try:
            slug=self._state.get_active_slug()
            if not slug:return BridgeResponse(success=False,error="No brand selected").to_dict()
            images=list_template_images(slug,template_slug)
            return BridgeResponse(success=True,data={"images":images}).to_dict()
        except Exception as e:return BridgeResponse(success=False,error=str(e)).to_dict()
    def upload_template_image(self,template_slug:str,filename:str,data_base64:str)->dict:
        """Upload an image to a template."""
        try:
            slug=self._state.get_active_slug()
            if not slug:return BridgeResponse(success=False,error="No brand selected").to_dict()
            if"/"in filename or"\\"in filename:return BridgeResponse(success=False,error="Invalid filename").to_dict()
            ext=Path(filename).suffix.lower()
            if ext not in ALLOWED_IMAGE_EXTS:return BridgeResponse(success=False,error="Unsupported file type").to_dict()
            content=base64.b64decode(data_base64);brand_relative_path=add_template_image(slug,template_slug,filename,content)
            return BridgeResponse(success=True,data={"path":brand_relative_path}).to_dict()
        except Exception as e:return BridgeResponse(success=False,error=str(e)).to_dict()
    def delete_template_image(self,template_slug:str,filename:str)->dict:
        """Delete a template image."""
        try:
            slug=self._state.get_active_slug()
            if not slug:return BridgeResponse(success=False,error="No brand selected").to_dict()
            deleted=delete_template_image(slug,template_slug,filename)
            if not deleted:return BridgeResponse(success=False,error=f"Image '{filename}' not found").to_dict()
            return BridgeResponse(success=True).to_dict()
        except Exception as e:return BridgeResponse(success=False,error=str(e)).to_dict()
    def set_primary_template_image(self,template_slug:str,filename:str)->dict:
        """Set the primary image for a template."""
        try:
            slug=self._state.get_active_slug()
            if not slug:return BridgeResponse(success=False,error="No brand selected").to_dict()
            template=load_template(slug,template_slug)
            if not template:return BridgeResponse(success=False,error=f"Template '{template_slug}' not found").to_dict()
            brand_relative_path=f"templates/{template_slug}/images/{filename}"
            if brand_relative_path not in template.images:return BridgeResponse(success=False,error=f"Image '{filename}' not found in template").to_dict()
            success=set_primary_template_image(slug,template_slug,brand_relative_path)
            if not success:return BridgeResponse(success=False,error="Failed to set primary image").to_dict()
            return BridgeResponse(success=True).to_dict()
        except Exception as e:return BridgeResponse(success=False,error=str(e)).to_dict()
    def get_template_image_thumbnail(self,path:str)->dict:
        """Get base64-encoded thumbnail for a template image."""
        try:
            if not path.startswith("templates/"):return BridgeResponse(success=False,error="Path must start with 'templates/'").to_dict()
            brand_dir,err=self._state.get_brand_dir()
            if err:return BridgeResponse(success=False,error=err).to_dict()
            resolved,error=resolve_in_dir(brand_dir,path)
            if error:return BridgeResponse(success=False,error=error).to_dict()
            if not resolved.exists():return BridgeResponse(success=False,error="Image not found").to_dict()
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
    def get_template_image_full(self,path:str)->dict:
        """Get base64-encoded full-resolution template image."""
        try:
            if not path.startswith("templates/"):return BridgeResponse(success=False,error="Path must start with 'templates/'").to_dict()
            brand_dir,err=self._state.get_brand_dir()
            if err:return BridgeResponse(success=False,error=err).to_dict()
            resolved,error=resolve_in_dir(brand_dir,path)
            if error:return BridgeResponse(success=False,error=error).to_dict()
            if not resolved.exists():return BridgeResponse(success=False,error="Image not found").to_dict()
            suffix=resolved.suffix.lower()
            if suffix not in ALLOWED_IMAGE_EXTS:return BridgeResponse(success=False,error="Unsupported file type").to_dict()
            content=resolved.read_bytes();encoded=base64.b64encode(content).decode("utf-8")
            mime_types={".png":"image/png",".jpg":"image/jpeg",".jpeg":"image/jpeg",".gif":"image/gif",".webp":"image/webp",".svg":"image/svg+xml"}
            mime=mime_types.get(suffix,"image/png")
            return BridgeResponse(success=True,data={"dataUrl":f"data:{mime};base64,{encoded}"}).to_dict()
        except Exception as e:return BridgeResponse(success=False,error=str(e)).to_dict()
