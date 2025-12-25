"""Python bridge exposed to JavaScript - thin facade delegating to services."""
from .state import BridgeState
from .services.asset_service import AssetService
from .services.brand_service import BrandService
from .services.chat_service import ChatService
from .services.document_service import DocumentService
from .services.image_status import ImageStatusService
from .services.product_service import ProductService
from .services.project_service import ProjectService
from .services.template_service import TemplateService
from .services.update_service import UpdateService
from .utils.bridge_types import BridgeResponse,bridge_ok,bridge_error
from .utils.config_store import check_api_keys as do_check_api_keys,load_api_keys_from_config,save_api_keys as do_save_api_keys
#Load API keys on module import (app startup)
load_api_keys_from_config()
class StudioBridge:
    """API exposed to the frontend via PyWebView."""
    def __init__(self):
        self._state=BridgeState()
        self._brand=BrandService(self._state)
        self._document=DocumentService(self._state)
        self._asset=AssetService(self._state)
        self._product=ProductService(self._state)
        self._project=ProjectService(self._state)
        self._template=TemplateService(self._state)
        self._chat=ChatService(self._state)
        self._update=UpdateService(self._state)
        self._image_status=ImageStatusService(self._state)
    def set_window(self,window):self._state.window=window
    #===========================================================================
    #Configuration / Setup
    #===========================================================================
    def check_api_keys(self)->dict:
        """Check if required API keys are configured."""
        return BridgeResponse(success=True,data=do_check_api_keys()).to_dict()
    def save_api_keys(self,openai_key:str,gemini_key:str,firecrawl_key:str="")->dict:
        """Save API keys to environment and persist to config file."""
        try:do_save_api_keys(openai_key,gemini_key,firecrawl_key);return BridgeResponse(success=True).to_dict()
        except Exception as e:return BridgeResponse(success=False,error=str(e)).to_dict()
    #===========================================================================
    #Brand Management
    #===========================================================================
    def get_brands(self)->dict:return self._brand.get_brands()
    def set_brand(self,slug:str)->dict:return self._brand.set_brand(slug)
    def get_brand_info(self,slug:str|None=None)->dict:return self._brand.get_brand_info(slug)
    def get_brand_identity(self)->dict:return self._brand.get_brand_identity()
    def update_brand_identity_section(self,section:str,data:dict)->dict:return self._brand.update_brand_identity_section(section,data)
    def regenerate_brand_identity(self,confirm:bool)->dict:return self._brand.regenerate_brand_identity(confirm)
    def list_identity_backups(self)->dict:return self._brand.list_identity_backups()
    def restore_identity_backup(self,filename:str)->dict:return self._brand.restore_identity_backup(filename)
    def delete_brand(self,slug:str)->dict:return self._brand.delete_brand(slug)
    def create_brand_from_materials(self,description:str,images:list[dict],documents:list[dict])->dict:return self._brand.create_brand_from_materials(description,images,documents)
    #===========================================================================
    #Document Management
    #===========================================================================
    def get_documents(self,slug:str|None=None)->dict:return self._document.get_documents(slug)
    def read_document(self,relative_path:str)->dict:return self._document.read_document(relative_path)
    def upload_document(self,filename:str,data_base64:str)->dict:return self._document.upload_document(filename,data_base64)
    def delete_document(self,relative_path:str)->dict:return self._document.delete_document(relative_path)
    def rename_document(self,relative_path:str,new_name:str)->dict:return self._document.rename_document(relative_path,new_name)
    def open_document_in_finder(self,relative_path:str)->dict:return self._document.open_document_in_finder(relative_path)
    #===========================================================================
    #Asset Management
    #===========================================================================
    def get_assets(self,slug:str|None=None)->dict:return self._asset.get_assets(slug)
    def get_asset_thumbnail(self,relative_path:str)->dict:return self._asset.get_asset_thumbnail(relative_path)
    def get_asset_full(self,relative_path:str)->dict:return self._asset.get_asset_full(relative_path)
    def get_image_thumbnail(self,image_path:str)->dict:return self._asset.get_image_thumbnail(image_path)
    def get_image_data(self,image_path:str)->dict:return self._asset.get_image_data(image_path)
    def upload_asset(self,filename:str,data_base64:str,category:str="generated")->dict:return self._asset.upload_asset(filename,data_base64,category)
    def delete_asset(self,relative_path:str)->dict:return self._asset.delete_asset(relative_path)
    def rename_asset(self,relative_path:str,new_name:str)->dict:return self._asset.rename_asset(relative_path,new_name)
    def open_asset_in_finder(self,relative_path:str)->dict:return self._asset.open_asset_in_finder(relative_path)
    def get_video_path(self,relative_path:str)->dict:return self._asset.get_video_path(relative_path)
    def get_video_data(self,relative_path:str)->dict:return self._asset.get_video_data(relative_path)
    #===========================================================================
    #Product Management
    #===========================================================================
    def get_products(self,brand_slug:str|None=None)->dict:return self._product.get_products(brand_slug)
    def get_product(self,product_slug:str)->dict:return self._product.get_product(product_slug)
    def create_product(self,name:str,description:str,images:list[dict]|None=None,attributes:list[dict]|None=None)->dict:return self._product.create_product(name,description,images,attributes)
    def update_product(self,product_slug:str,name:str|None=None,description:str|None=None,attributes:list[dict]|None=None)->dict:return self._product.update_product(product_slug,name,description,attributes)
    def delete_product(self,product_slug:str)->dict:return self._product.delete_product(product_slug)
    def get_product_images(self,product_slug:str)->dict:return self._product.get_product_images(product_slug)
    def upload_product_image(self,product_slug:str,filename:str,data_base64:str)->dict:return self._product.upload_product_image(product_slug,filename,data_base64)
    def delete_product_image(self,product_slug:str,filename:str)->dict:return self._product.delete_product_image(product_slug,filename)
    def set_primary_product_image(self,product_slug:str,filename:str)->dict:return self._product.set_primary_product_image(product_slug,filename)
    def get_product_image_thumbnail(self,path:str)->dict:return self._product.get_product_image_thumbnail(path)
    def get_product_image_full(self,path:str)->dict:return self._product.get_product_image_full(path)
    #===========================================================================
    #Template Management
    #===========================================================================
    def get_templates(self,brand_slug:str|None=None)->dict:return self._template.get_templates(brand_slug)
    def get_template(self,template_slug:str)->dict:return self._template.get_template(template_slug)
    def create_template(self,name:str,description:str,images:list[dict]|None=None,default_strict:bool=True)->dict:return self._template.create_template(name,description,images,default_strict)
    def update_template(self,template_slug:str,name:str|None=None,description:str|None=None,default_strict:bool|None=None)->dict:return self._template.update_template(template_slug,name,description,default_strict)
    def delete_template(self,template_slug:str)->dict:return self._template.delete_template(template_slug)
    def get_template_images(self,template_slug:str)->dict:return self._template.get_template_images(template_slug)
    def upload_template_image(self,template_slug:str,filename:str,data_base64:str)->dict:return self._template.upload_template_image(template_slug,filename,data_base64)
    def delete_template_image(self,template_slug:str,filename:str)->dict:return self._template.delete_template_image(template_slug,filename)
    def set_primary_template_image(self,template_slug:str,filename:str)->dict:return self._template.set_primary_template_image(template_slug,filename)
    def get_template_image_thumbnail(self,path:str)->dict:return self._template.get_template_image_thumbnail(path)
    def get_template_image_full(self,path:str)->dict:return self._template.get_template_image_full(path)
    def reanalyze_template(self,template_slug:str)->dict:return self._template.reanalyze_template(template_slug)
    #===========================================================================
    #Project Management
    #===========================================================================
    def get_projects(self,brand_slug:str|None=None)->dict:return self._project.get_projects(brand_slug)
    def get_project(self,project_slug:str)->dict:return self._project.get_project(project_slug)
    def create_project(self,name:str,instructions:str="")->dict:return self._project.create_project(name,instructions)
    def update_project(self,project_slug:str,name:str|None=None,instructions:str|None=None,status:str|None=None)->dict:return self._project.update_project(project_slug,name,instructions,status)
    def delete_project(self,project_slug:str)->dict:return self._project.delete_project(project_slug)
    def set_active_project(self,project_slug:str|None)->dict:return self._project.set_active_project(project_slug)
    def get_active_project(self)->dict:return self._project.get_active_project()
    def get_project_assets(self,project_slug:str)->dict:return self._project.get_project_assets(project_slug)
    def get_general_assets(self,brand_slug:str|None=None)->dict:return self._project.get_general_assets(brand_slug)
    #===========================================================================
    #Chat
    #===========================================================================
    def chat(self,message:str,attachments:list[dict]|None=None,project_slug:str|None=None,attached_products:list[str]|None=None,attached_templates:list[dict]|None=None)->dict:return self._chat.chat(message,attachments,project_slug,attached_products,attached_templates)
    def clear_chat(self)->dict:return self._chat.clear_chat()
    def refresh_brand_memory(self)->dict:return self._chat.refresh_brand_memory()
    def get_progress(self)->dict:return self._chat.get_progress()
    #===========================================================================
    #App Updates
    #===========================================================================
    def get_app_version(self)->dict:return self._update.get_app_version()
    def check_for_updates(self)->dict:return self._update.check_for_updates()
    def download_and_install_update(self,download_url:str,version:str)->dict:return self._update.download_and_install_update(download_url,version)
    def get_update_progress(self)->dict:return self._update.get_update_progress()
    def skip_update_version(self,version:str)->dict:return self._update.skip_update_version(version)
    def get_update_settings(self)->dict:return self._update.get_update_settings()
    def set_update_check_on_startup(self,enabled:bool)->dict:return self._update.set_update_check_on_startup(enabled)
    #===========================================================================
    #Image Status (Workstation Curation)
    #===========================================================================
    def get_unsorted_images(self,brand_slug:str|None=None)->dict:
        """Get all unsorted images for a brand."""
        slug=brand_slug or self._state.get_active_slug()
        if not slug:return bridge_error("No brand selected")
        return self._image_status.list_by_status(slug,"unsorted")
    def get_images_by_status(self,brand_slug:str|None=None,status:str="unsorted")->dict:
        """Get images filtered by status."""
        slug=brand_slug or self._state.get_active_slug()
        if not slug:return bridge_error("No brand selected")
        return self._image_status.list_by_status(slug,status)
    def mark_image_kept(self,image_id:str,brand_slug:str|None=None)->dict:
        """Mark image as kept and move to kept/ folder."""
        slug=brand_slug or self._state.get_active_slug()
        if not slug:return bridge_error("No brand selected")
        return self._move_image_to_status(slug,image_id,"kept")
    def mark_image_trashed(self,image_id:str,brand_slug:str|None=None)->dict:
        """Mark image as trashed and move to trash/ folder."""
        slug=brand_slug or self._state.get_active_slug()
        if not slug:return bridge_error("No brand selected")
        return self._move_image_to_status(slug,image_id,"trashed")
    def trash_by_path(self,path:str,brand_slug:str|None=None)->dict:
        """Trash an image by its file path (relative or absolute). Registers it first if not tracked."""
        from pathlib import Path
        from sip_videogen.brands.storage import get_brand_dir
        from sip_videogen.studio.utils.path_utils import resolve_assets_path
        slug=brand_slug or self._state.get_active_slug()
        if not slug:return bridge_error("No brand selected")
        #Resolve relative path to absolute if needed
        full_path=path
        if not Path(path).is_absolute():
            brand_dir=get_brand_dir(slug)
            resolved,err=resolve_assets_path(brand_dir,path)
            if err:return bridge_error(err)
            if resolved:full_path=str(resolved)
        #Find or register the image
        result=self._image_status.register_or_find(slug,full_path,"kept")
        if not result.get("success"):return result
        image_id=result.get("data",{}).get("id")
        if not image_id:return bridge_error("Failed to get image ID")
        return self._move_image_to_status(slug,image_id,"trashed")
    def unkeep_image(self,image_id:str,brand_slug:str|None=None)->dict:
        """Return kept image to unsorted status."""
        slug=brand_slug or self._state.get_active_slug()
        if not slug:return bridge_error("No brand selected")
        return self._move_image_to_status(slug,image_id,"unsorted")
    def restore_image(self,image_id:str,brand_slug:str|None=None)->dict:
        """Restore trashed image to unsorted status."""
        slug=brand_slug or self._state.get_active_slug()
        if not slug:return bridge_error("No brand selected")
        return self._move_image_to_status(slug,image_id,"unsorted")
    def empty_trash(self,brand_slug:str|None=None)->dict:
        """Permanently delete all trashed images."""
        from pathlib import Path
        slug=brand_slug or self._state.get_active_slug()
        if not slug:return bridge_error("No brand selected")
        try:
            result=self._image_status.list_by_status(slug,"trashed")
            if not result.get("success"):return result
            trashed=result.get("data",[]);deleted=[]
            for entry in trashed:
                path=Path(entry.get("currentPath",""))
                if path.exists():
                    try:path.unlink()
                    except OSError:pass
                self._image_status.delete_image(slug,entry["id"]);deleted.append(entry["id"])
            return bridge_ok({"deleted":deleted,"count":len(deleted)})
        except Exception as e:return bridge_error(str(e))
    def register_image(self,image_path:str,brand_slug:str|None=None,prompt:str|None=None,source_template_path:str|None=None)->dict:
        """Register a new image with unsorted status."""
        slug=brand_slug or self._state.get_active_slug()
        if not slug:return bridge_error("No brand selected")
        return self._image_status.register_image(slug,image_path,prompt,source_template_path)
    def register_generated_images(self,images:list[dict],brand_slug:str|None=None)->dict:
        """Register multiple generated images at once."""
        slug=brand_slug or self._state.get_active_slug()
        if not slug:return bridge_error("No brand selected")
        try:
            registered=[]
            for img in images:
                path=img.get("path","");prompt=img.get("prompt");src=img.get("sourceTemplatePath")
                result=self._image_status.register_image(slug,path,prompt,src)
                if result.get("success"):registered.append(result.get("data"))
            return bridge_ok(registered)
        except Exception as e:return bridge_error(str(e))
    def cancel_generation(self,brand_slug:str|None=None)->dict:
        """Cancel ongoing image generation (placeholder for future implementation)."""
        return bridge_ok({"cancelled":True})
    def cleanup_old_trash(self,brand_slug:str|None=None,days:int=30)->dict:
        """Delete trash items older than specified days."""
        slug=brand_slug or self._state.get_active_slug()
        if not slug:return bridge_error("No brand selected")
        return self._image_status.cleanup_old_trash(slug,days)
    def backfill_images(self,brand_slug:str|None=None)->dict:
        """Backfill image status from existing folders. Called on brand selection."""
        slug=brand_slug or self._state.get_active_slug()
        if not slug:return bridge_error("No brand selected")
        return self._image_status.backfill_from_folders(slug)
    def copy_image_to_clipboard(self,image_path:str)->dict:
        """Copy image file to system clipboard (macOS)."""
        import subprocess
        from pathlib import Path
        try:
            path=Path(image_path)
            if not path.exists():return bridge_error(f"File not found: {image_path}")
            script=f'''osascript -e 'set the clipboard to (read (POSIX file "{path}") as «class PNGf»)' 2>/dev/null || osascript -e 'set the clipboard to (read (POSIX file "{path}") as JPEG picture)' '''
            subprocess.run(script,shell=True,check=True,capture_output=True)
            return bridge_ok({"copied":True,"path":str(path)})
        except subprocess.CalledProcessError as e:return bridge_error(f"Failed to copy: {e}")
        except Exception as e:return bridge_error(str(e))
    def share_image(self,image_path:str)->dict:
        """Open macOS share sheet for image."""
        import subprocess
        from pathlib import Path
        try:
            path=Path(image_path)
            if not path.exists():return bridge_error(f"File not found: {image_path}")
            script=f'''osascript -e 'tell application "Finder" to reveal POSIX file "{path}"' -e 'tell application "System Events" to keystroke "," using {{command down, shift down}}' '''
            subprocess.Popen(["open","-R",str(path)])
            return bridge_ok({"shared":True,"path":str(path)})
        except Exception as e:return bridge_error(str(e))
    def _move_image_to_status(self,brand_slug:str,image_id:str,new_status:str)->dict:
        """Move image file to appropriate folder and update status."""
        import shutil
        from pathlib import Path
        from sip_videogen.brands.storage import get_brand_dir
        try:
            status_result=self._image_status.get_status(brand_slug,image_id)
            if not status_result.get("success"):return status_result
            entry=status_result.get("data",{});current_path=Path(entry.get("currentPath",""))
            if not current_path.exists():return bridge_error(f"File not found: {current_path}")
            brand_dir=get_brand_dir(brand_slug);assets_dir=brand_dir/"assets"
            folder_map={"unsorted":"generated","kept":"kept","trashed":"trash"}
            target_folder=assets_dir/folder_map.get(new_status,"generated")
            target_folder.mkdir(parents=True,exist_ok=True)
            new_path=target_folder/current_path.name
            if new_path!=current_path:
                if new_path.exists():
                    stem=current_path.stem;suffix=current_path.suffix;counter=1
                    while new_path.exists():new_path=target_folder/f"{stem}_{counter}{suffix}";counter+=1
                shutil.move(str(current_path),str(new_path))
            self._image_status.set_status(brand_slug,image_id,new_status)
            self._image_status.update_path(brand_slug,image_id,str(new_path))
            updated=self._image_status.get_status(brand_slug,image_id)
            return updated if updated.get("success")else bridge_ok({"id":image_id,"status":new_status,"currentPath":str(new_path)})
        except Exception as e:return bridge_error(str(e))
