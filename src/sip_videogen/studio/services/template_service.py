"""Template management service."""
from __future__ import annotations
import asyncio,base64,io,re
from datetime import datetime
from pathlib import Path
from sip_videogen.brands.models import TemplateFull
from sip_videogen.brands.storage import(add_template_image,create_template,delete_template,delete_template_image,get_template_dir,list_template_images,list_templates,load_template,save_template,set_primary_template_image)
from sip_videogen.advisor.template_analyzer import analyze_template_v2
from sip_videogen.config.logging import get_logger
from ..state import BridgeState
from ..utils.bridge_types import ALLOWED_IMAGE_EXTS,bridge_ok,bridge_error
from ..utils.path_utils import resolve_in_dir
logger=get_logger(__name__)
class TemplateService:
    """Template CRUD and image operations."""
    def __init__(self,state:BridgeState):self._state=state
    def get_templates(self,brand_slug:str|None=None)->dict:
        """Get list of templates for a brand."""
        try:
            target_slug=brand_slug or self._state.get_active_slug()
            if not target_slug:return bridge_error("No brand selected")
            templates=list_templates(target_slug)
            return bridge_ok({"templates":[{"slug":t.slug,"name":t.name,"description":t.description,"primary_image":t.primary_image,"default_strict":t.default_strict,"created_at":t.created_at.isoformat(),"updated_at":t.updated_at.isoformat()}for t in templates]})
        except Exception as e:return bridge_error(str(e))
    def get_template(self,template_slug:str)->dict:
        """Get detailed template information."""
        try:
            slug=self._state.get_active_slug()
            if not slug:return bridge_error("No brand selected")
            template=load_template(slug,template_slug)
            if not template:return bridge_error(f"Template '{template_slug}' not found")
            analysis_data=None
            if template.analysis:analysis_data=template.analysis.model_dump()
            return bridge_ok({"slug":template.slug,"name":template.name,"description":template.description,"images":template.images,"primary_image":template.primary_image,"default_strict":template.default_strict,"analysis":analysis_data,"created_at":template.created_at.isoformat(),"updated_at":template.updated_at.isoformat()})
        except Exception as e:return bridge_error(str(e))
    def create_template(self,name:str,description:str,images:list[dict]|None=None,default_strict:bool=True)->dict:
        """Create a new template."""
        try:
            slug=self._state.get_active_slug()
            if not slug:return bridge_error("No brand selected")
            if not name.strip():return bridge_error("Template name is required")
            template_slug=re.sub(r"[^a-z0-9]+","-",name.lower()).strip("-")
            if not template_slug:return bridge_error("Invalid template name")
            if load_template(slug,template_slug):return bridge_error(f"Template '{template_slug}' already exists")
            now=datetime.utcnow()
            template=TemplateFull(slug=template_slug,name=name.strip(),description=description.strip(),images=[],primary_image="",default_strict=default_strict,analysis=None,created_at=now,updated_at=now)
            create_template(slug,template)
            #Upload images
            if images:
                for img in images:
                    filename=img.get("filename","");data_b64=img.get("data","")
                    if not filename or not data_b64:continue
                    ext=Path(filename).suffix.lower()
                    if ext not in ALLOWED_IMAGE_EXTS:continue
                    try:content=base64.b64decode(data_b64);add_template_image(slug,template_slug,filename,content)
                    except Exception as e:logger.warning("Failed to add template image %s: %s",filename,e)
            #Run V2 analyzer on uploaded images
            template=load_template(slug,template_slug)
            if template and template.images:
                template_dir=get_template_dir(slug,template_slug)
                img_paths=[template_dir/"images"/Path(p).name for p in template.images if(template_dir/"images"/Path(p).name).exists()]
                if img_paths:
                    try:
                        analysis=asyncio.get_event_loop().run_until_complete(analyze_template_v2(img_paths[:2]))
                        if analysis:template.analysis=analysis;template.updated_at=datetime.utcnow();save_template(slug,template)
                    except RuntimeError:
                        analysis=asyncio.run(analyze_template_v2(img_paths[:2]))
                        if analysis:template.analysis=analysis;template.updated_at=datetime.utcnow();save_template(slug,template)
            return bridge_ok({"slug":template_slug})
        except Exception as e:return bridge_error(str(e))
    def update_template(self,template_slug:str,name:str|None=None,description:str|None=None,default_strict:bool|None=None)->dict:
        """Update an existing template."""
        try:
            slug=self._state.get_active_slug()
            if not slug:return bridge_error("No brand selected")
            template=load_template(slug,template_slug)
            if not template:return bridge_error(f"Template '{template_slug}' not found")
            if name is not None:template.name=name.strip()
            if description is not None:template.description=description.strip()
            if default_strict is not None:template.default_strict=default_strict
            template.updated_at=datetime.utcnow();save_template(slug,template)
            return bridge_ok({"slug":template.slug,"name":template.name,"description":template.description,"default_strict":template.default_strict})
        except Exception as e:return bridge_error(str(e))
    def reanalyze_template(self,template_slug:str)->dict:
        """Re-run V2 Gemini analysis on template images."""
        try:
            slug=self._state.get_active_slug()
            if not slug:return bridge_error("No brand selected")
            template=load_template(slug,template_slug)
            if not template:return bridge_error(f"Template '{template_slug}' not found")
            if not template.images:return bridge_error("No images to analyze")
            template_dir=get_template_dir(slug,template_slug)
            img_paths=[template_dir/"images"/Path(p).name for p in template.images if(template_dir/"images"/Path(p).name).exists()]
            if not img_paths:return bridge_error("No valid image files found")
            try:
                analysis=asyncio.get_event_loop().run_until_complete(analyze_template_v2(img_paths[:2]))
            except RuntimeError:
                analysis=asyncio.run(analyze_template_v2(img_paths[:2]))
            if not analysis:return bridge_error("Analysis failed - check Gemini API key")
            template.analysis=analysis;template.updated_at=datetime.utcnow();save_template(slug,template)
            return bridge_ok({"analysis":analysis.model_dump()})
        except Exception as e:return bridge_error(str(e))
    def delete_template(self,template_slug:str)->dict:
        """Delete a template and all its files."""
        try:
            slug=self._state.get_active_slug()
            if not slug:return bridge_error("No brand selected")
            deleted=delete_template(slug,template_slug)
            if not deleted:return bridge_error(f"Template '{template_slug}' not found")
            return bridge_ok()
        except Exception as e:return bridge_error(str(e))
    def get_template_images(self,template_slug:str)->dict:
        """Get list of images for a template."""
        try:
            slug=self._state.get_active_slug()
            if not slug:return bridge_error("No brand selected")
            images=list_template_images(slug,template_slug)
            return bridge_ok({"images":images})
        except Exception as e:return bridge_error(str(e))
    def upload_template_image(self,template_slug:str,filename:str,data_base64:str)->dict:
        """Upload an image to a template."""
        try:
            slug=self._state.get_active_slug()
            if not slug:return bridge_error("No brand selected")
            if"/"in filename or"\\"in filename:return bridge_error("Invalid filename")
            ext=Path(filename).suffix.lower()
            if ext not in ALLOWED_IMAGE_EXTS:return bridge_error("Unsupported file type")
            content=base64.b64decode(data_base64);brand_relative_path=add_template_image(slug,template_slug,filename,content)
            return bridge_ok({"path":brand_relative_path})
        except Exception as e:return bridge_error(str(e))
    def delete_template_image(self,template_slug:str,filename:str)->dict:
        """Delete a template image."""
        try:
            slug=self._state.get_active_slug()
            if not slug:return bridge_error("No brand selected")
            deleted=delete_template_image(slug,template_slug,filename)
            if not deleted:return bridge_error(f"Image '{filename}' not found")
            return bridge_ok()
        except Exception as e:return bridge_error(str(e))
    def set_primary_template_image(self,template_slug:str,filename:str)->dict:
        """Set the primary image for a template."""
        try:
            slug=self._state.get_active_slug()
            if not slug:return bridge_error("No brand selected")
            template=load_template(slug,template_slug)
            if not template:return bridge_error(f"Template '{template_slug}' not found")
            brand_relative_path=f"templates/{template_slug}/images/{filename}"
            if brand_relative_path not in template.images:return bridge_error(f"Image '{filename}' not found in template")
            success=set_primary_template_image(slug,template_slug,brand_relative_path)
            if not success:return bridge_error("Failed to set primary image")
            return bridge_ok()
        except Exception as e:return bridge_error(str(e))
    def get_template_image_thumbnail(self,path:str)->dict:
        """Get base64-encoded thumbnail for a template image."""
        try:
            if not path.startswith("templates/"):return bridge_error("Path must start with 'templates/'")
            brand_dir,err=self._state.get_brand_dir()
            if err:return bridge_error(err)
            resolved,error=resolve_in_dir(brand_dir,path)
            if error:return bridge_error(error)
            if not resolved.exists():return bridge_error("Image not found")
            suffix=resolved.suffix.lower()
            if suffix not in ALLOWED_IMAGE_EXTS:return bridge_error("Unsupported file type")
            if suffix==".svg":
                content=resolved.read_bytes();encoded=base64.b64encode(content).decode("utf-8")
                return bridge_ok({"dataUrl":f"data:image/svg+xml;base64,{encoded}"})
            from PIL import Image
            with Image.open(resolved)as img:
                img=img.convert("RGBA");img.thumbnail((256,256))
                buf=io.BytesIO();img.save(buf,format="PNG")
                encoded=base64.b64encode(buf.getvalue()).decode("utf-8")
            return bridge_ok({"dataUrl":f"data:image/png;base64,{encoded}"})
        except Exception as e:return bridge_error(str(e))
    def get_template_image_full(self,path:str)->dict:
        """Get base64-encoded full-resolution template image."""
        try:
            if not path.startswith("templates/"):return bridge_error("Path must start with 'templates/'")
            brand_dir,err=self._state.get_brand_dir()
            if err:return bridge_error(err)
            resolved,error=resolve_in_dir(brand_dir,path)
            if error:return bridge_error(error)
            if not resolved.exists():return bridge_error("Image not found")
            suffix=resolved.suffix.lower()
            if suffix not in ALLOWED_IMAGE_EXTS:return bridge_error("Unsupported file type")
            content=resolved.read_bytes();encoded=base64.b64encode(content).decode("utf-8")
            mime_types={".png":"image/png",".jpg":"image/jpeg",".jpeg":"image/jpeg",".gif":"image/gif",".webp":"image/webp",".svg":"image/svg+xml"}
            mime=mime_types.get(suffix,"image/png")
            return bridge_ok({"dataUrl":f"data:{mime};base64,{encoded}"})
        except Exception as e:return bridge_error(str(e))
