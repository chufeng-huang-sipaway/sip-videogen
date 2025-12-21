"""Chat coordination service."""
from __future__ import annotations
import asyncio,time
from pathlib import Path
from sip_videogen.advisor.agent import BrandAdvisor
from sip_videogen.advisor.tools import get_image_metadata
from sip_videogen.brands.memory import list_brand_assets
from sip_videogen.brands.storage import get_active_brand,get_active_project,get_brand_dir,set_active_project
from sip_videogen.config.logging import get_logger
from ..state import BridgeState
from ..utils.bridge_types import BridgeResponse
from ..utils.chat_utils import analyze_and_format_attachments,encode_new_images,process_attachments
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
    def get_progress(self)->dict:
        """Get current operation progress."""
        return BridgeResponse(success=True,data={"status":self._state.current_progress,"type":self._state.current_progress_type,"skills":self._state.matched_skills}).to_dict()
    def chat(self,message:str,attachments:list[dict]|None=None,project_slug:str|None=None,attached_products:list[str]|None=None)->dict:
        """Send a message to the Brand Advisor with optional context."""
        self._state.execution_trace=[];self._state.matched_skills=[]
        try:
            if self._state.advisor is None:
                active=get_active_brand()
                if active:self._state.advisor=BrandAdvisor(brand_slug=active,progress_callback=self._progress_callback);self._state.current_brand=active
                else:return BridgeResponse(success=False,error="No brand selected").to_dict()
            slug=self._state.get_active_slug()
            if not slug:return BridgeResponse(success=False,error="No brand selected").to_dict()
            global_active_brand=get_active_brand()
            logger.debug("chat(): slug=%s, global_active_brand=%s, project_slug=%s",slug,global_active_brand,project_slug)
            if slug!=global_active_brand:logger.warning("BRAND MISMATCH: _get_active_slug()=%s but get_active_brand()=%s",slug,global_active_brand)
            if project_slug is not None:logger.debug("chat(): Setting active project to %s",project_slug);set_active_project(slug,project_slug)
            effective_project=project_slug if project_slug is not None else get_active_project(slug)
            if project_slug is None:logger.info("chat(): effective_project from storage: %s",effective_project)
            brand_dir=get_brand_dir(slug)
            #Process attachments
            saved_attachments=asyncio.run(process_attachments(attachments,brand_dir,lambda p:resolve_assets_path(brand_dir,p),lambda p:resolve_docs_path(brand_dir,p)))
            prepared_message=message.strip()or"Please review the attached files."
            if saved_attachments:
                analysis_text=asyncio.run(analyze_and_format_attachments(saved_attachments,brand_dir))
                if analysis_text:prepared_message=f"{prepared_message}\n\n{analysis_text}".strip()
            #Snapshot generated assets before running
            before={a["path"]for a in list_brand_assets(slug,category="generated")}
            #Run advisor
            result=asyncio.run(self._state.advisor.chat_with_metadata(prepared_message,project_slug=effective_project,attached_products=attached_products))
            response=result["response"];interaction=result.get("interaction");memory_update=result.get("memory_update")
            after={a["path"]for a in list_brand_assets(slug,category="generated")}
            new_paths=sorted(after-before)
            image_data=encode_new_images(new_paths,get_image_metadata)
            return BridgeResponse(success=True,data={"response":response,"images":image_data,"execution_trace":self._state.execution_trace,"interaction":interaction,"memory_update":memory_update}).to_dict()
        except Exception as e:return BridgeResponse(success=False,error=str(e)).to_dict()
        finally:self._state.current_progress=""
    def clear_chat(self)->dict:
        """Clear conversation history."""
        try:
            if self._state.advisor:
                slug=self._state.get_active_slug()
                if slug:self._state.advisor.set_brand(slug,preserve_history=False)
                else:self._state.advisor.clear_history()
            self._state.current_progress="";self._state.execution_trace=[]
            return BridgeResponse(success=True).to_dict()
        except Exception as e:return BridgeResponse(success=False,error=str(e)).to_dict()
    def refresh_brand_memory(self)->dict:
        """Refresh the agent's brand context."""
        try:
            slug=self._state.current_brand or get_active_brand()
            if not slug:return BridgeResponse(success=False,error="No brand selected").to_dict()
            if self._state.advisor is None:self._state.advisor=BrandAdvisor(brand_slug=slug,progress_callback=self._progress_callback)
            else:self._state.advisor.set_brand(slug,preserve_history=True)
            return BridgeResponse(success=True,data={"message":"Brand context refreshed"}).to_dict()
        except Exception as e:return BridgeResponse(success=False,error=str(e)).to_dict()
