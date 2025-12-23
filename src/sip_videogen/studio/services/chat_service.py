"""Chat coordination service."""
from __future__ import annotations
import asyncio
import time
from sip_videogen.advisor.agent import BrandAdvisor
from sip_videogen.advisor.tools import get_image_metadata,get_video_metadata
from sip_videogen.brands.memory import list_brand_assets,list_brand_videos
from sip_videogen.brands.storage import get_active_brand,get_active_project,get_brand_dir,set_active_project
from sip_videogen.config.logging import get_logger
from ..state import BridgeState
from ..utils.bridge_types import bridge_ok,bridge_error
from ..utils.chat_utils import analyze_and_format_attachments,encode_new_images,encode_new_videos,process_attachments
from ..utils.path_utils import resolve_assets_path,resolve_docs_path
logger=get_logger(__name__)
class ChatService:
    """Chat coordination with BrandAdvisor."""
    def __init__(self,state:BridgeState):self._state=state
    def _progress_callback(self,progress)->None:
        """Called by BrandAdvisor during execution."""
        event={"type":progress.event_type,"timestamp":int(time.time()*1000),"message":progress.message,"detail":progress.detail or""}
        self._state.execution_trace.append(event)
        if progress.event_type=="skill_loaded":
            skill_name=progress.message.replace("Loading ","").replace(" skill","")
            if skill_name not in self._state.matched_skills:self._state.matched_skills.append(skill_name)
        if progress.event_type=="tool_end":self._state.current_progress="";self._state.current_progress_type=""
        else:self._state.current_progress=progress.message;self._state.current_progress_type=progress.event_type
    def _ensure_advisor(self)->tuple[BrandAdvisor|None,str|None]:
        """Initialize or get the brand advisor."""
        if self._state.advisor is None:
            active=get_active_brand()
            if not active:return None,"No brand selected"
            self._state.advisor=BrandAdvisor(brand_slug=active,progress_callback=self._progress_callback)
        return self._state.advisor,None
    def _collect_new_images(self,slug:str,before:set[str])->list[dict]:
        """Find newly generated images and encode them."""
        after={a["path"]for a in list_brand_assets(slug,category="generated")}
        new_paths=sorted(after-before)
        return encode_new_images(new_paths,get_image_metadata)
    def _collect_new_videos(self,slug:str,before:set[str])->list[dict]:
        """Find newly generated videos and encode them."""
        after={a["path"]for a in list_brand_videos(slug)}
        new_paths=sorted(after-before)
        return encode_new_videos(new_paths,get_video_metadata)
    def get_progress(self)->dict:
        """Get current operation progress."""
        return bridge_ok({"status":self._state.current_progress,"type":self._state.current_progress_type,"skills":self._state.matched_skills})
    def chat(self,message:str,attachments:list[dict]|None=None,project_slug:str|None=None,attached_products:list[str]|None=None,attached_templates:list[dict]|None=None)->dict:
        """Send a message to the Brand Advisor with optional context."""
        self._state.execution_trace=[];self._state.matched_skills=[]
        try:
            advisor,err=self._ensure_advisor()
            if err or advisor is None:return bridge_error(err or "No brand selected")
            slug=self._state.get_active_slug()
            if not slug:return bridge_error("No brand selected")
            logger.debug("chat(): slug=%s, project_slug=%s",slug,project_slug)
            if project_slug is not None:logger.debug("chat(): Setting active project to %s",project_slug);set_active_project(slug,project_slug)
            effective_project=project_slug if project_slug is not None else get_active_project(slug)
            if project_slug is None:logger.info("chat(): effective_project from storage: %s",effective_project)
            brand_dir=get_brand_dir(slug)
            #Process attachments
            saved=asyncio.run(process_attachments(attachments,brand_dir,lambda p:resolve_assets_path(brand_dir,p),lambda p:resolve_docs_path(brand_dir,p)))
            prepared=message.strip()or"Please review the attached files."
            if saved:
                analysis=asyncio.run(analyze_and_format_attachments(saved,brand_dir))
                if analysis:prepared=f"{prepared}\n\n{analysis}".strip()
            #Snapshot generated assets before running
            before_images={a["path"]for a in list_brand_assets(slug,category="generated")}
            before_videos={a["path"]for a in list_brand_videos(slug)}
            #Run advisor
            result=asyncio.run(advisor.chat_with_metadata(prepared,project_slug=effective_project,attached_products=attached_products,attached_templates=attached_templates))
            response=result["response"];interaction=result.get("interaction");memory_update=result.get("memory_update")
            images=self._collect_new_images(slug,before_images)
            videos=self._collect_new_videos(slug,before_videos)
            return bridge_ok({"response":response,"images":images,"videos":videos,"execution_trace":self._state.execution_trace,"interaction":interaction,"memory_update":memory_update})
        except Exception as e:return bridge_error(str(e))
        finally:self._state.current_progress=""
    def clear_chat(self)->dict:
        """Clear conversation history."""
        try:
            if self._state.advisor:
                slug=self._state.get_active_slug()
                if slug:self._state.advisor.set_brand(slug,preserve_history=False)
                else:self._state.advisor.clear_history()
            self._state.current_progress="";self._state.execution_trace=[]
            return bridge_ok()
        except Exception as e:return bridge_error(str(e))
    def refresh_brand_memory(self)->dict:
        """Refresh the agent's brand context."""
        try:
            slug=get_active_brand()
            if not slug:return bridge_error("No brand selected")
            if self._state.advisor is None:self._state.advisor=BrandAdvisor(brand_slug=slug,progress_callback=self._progress_callback)
            else:self._state.advisor.set_brand(slug,preserve_history=True)
            return bridge_ok({"message":"Brand context refreshed"})
        except Exception as e:return bridge_error(str(e))
