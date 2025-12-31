"""Inspiration generation service for proactive creative ideas."""
from __future__ import annotations
import asyncio,threading,time,uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from PIL import Image
from sip_videogen.brands.context import BrandContextBuilder
from sip_videogen.brands.inspirations import(Inspiration,InspirationBatch,InspirationIdea,InspirationImage,InspirationJob,cleanup_old_inspirations,list_inspirations,load_inspiration,load_inspiration_meta,save_inspiration,save_inspiration_meta,delete_inspiration)
from sip_videogen.brands.storage import get_active_brand,get_brand_dir
from sip_videogen.config.logging import get_logger
from sip_videogen.config.settings import get_settings
from ..state import BridgeState
from ..utils.bridge_types import bridge_ok,bridge_error
logger=get_logger(__name__)
_PROMPT_PATH=Path(__file__).parent.parent.parent/"advisor"/"prompts"/"inspiration_system.md"
class InspirationService:
    """Service for generating and managing brand inspirations."""
    _executor:ThreadPoolExecutor|None=None
    _executor_lock=threading.Lock()
    def __init__(self,state:BridgeState):
        self._state=state
        self._jobs:dict[str,InspirationJob]={}
        self._jobs_lock=threading.Lock()
        self._cancel_events:dict[str,threading.Event]={}
    @classmethod
    def _get_executor(cls)->ThreadPoolExecutor:
        """Get or create shared executor (max 6 concurrent image generations)."""
        with cls._executor_lock:
            if cls._executor is None:cls._executor=ThreadPoolExecutor(max_workers=6,thread_name_prefix="insp_")
            return cls._executor
    def _load_system_prompt(self)->str:
        """Load the inspiration system prompt template."""
        if _PROMPT_PATH.exists():return _PROMPT_PATH.read_text()
        return"You are a creative brand manager. Generate 2-3 creative inspiration ideas for the brand."
    def _build_brand_context(self,brand_slug:str)->str:
        """Build brand context for inspiration generation."""
        try:
            builder=BrandContextBuilder(brand_slug)
            return builder.build_context_section()
        except Exception as e:
            logger.error(f"Failed to build brand context: {e}")
            return""
    def get_inspirations(self,brand_slug:str|None=None)->dict:
        """Get all inspirations for a brand."""
        slug=brand_slug or get_active_brand()
        if not slug:return bridge_ok({"inspirations":[],"job":None})
        try:
            insps=list_inspirations(slug)
            #Filter out dismissed, return ready and generating
            active=[i for i in insps if i.status in("ready","generating","saved")]
            #Check for active job
            job=None
            with self._jobs_lock:
                for j in self._jobs.values():
                    if j.brand_slug==slug and j.status in("pending","generating"):
                        job=j.to_dict()
                        break
            return bridge_ok({"inspirations":[i.to_dict()for i in active],"job":job})
        except Exception as e:
            logger.error(f"get_inspirations error: {e}")
            return bridge_error(str(e))
    def trigger_generation(self,brand_slug:str|None=None)->dict:
        """Trigger inspiration generation for a brand. Returns job ID."""
        slug=brand_slug or get_active_brand()
        if not slug:return bridge_error("No brand selected")
        #Check if already generating for this brand
        with self._jobs_lock:
            for j in self._jobs.values():
                if j.brand_slug==slug and j.status in("pending","generating"):
                    return bridge_ok({"job_id":j.id,"message":"Generation already in progress"})
        #Check throttle (5 min between auto-generations)
        meta=load_inspiration_meta(slug)
        if meta.last_generated_at:
            try:
                last=datetime.fromisoformat(meta.last_generated_at.replace("Z","+00:00"))
                elapsed=(datetime.utcnow()-last.replace(tzinfo=None)).total_seconds()
                if elapsed<300:
                    return bridge_ok({"job_id":None,"message":f"Please wait {int(300-elapsed)}s before generating again"})
            except:pass
        #Clean up old inspirations first
        try:cleanup_old_inspirations(slug)
        except Exception as e:logger.warning(f"Cleanup failed: {e}")
        #Create job
        job=InspirationJob(brand_slug=slug,status="pending",total_inspirations=3)
        cancel_event=threading.Event()
        with self._jobs_lock:
            self._jobs[job.id]=job
            self._cancel_events[job.id]=cancel_event
        #Submit to executor
        executor=self._get_executor()
        executor.submit(self._run_generation,job.id,slug,cancel_event)
        return bridge_ok({"job_id":job.id})
    def get_progress(self,job_id:str)->dict:
        """Get progress of a generation job."""
        with self._jobs_lock:
            job=self._jobs.get(job_id)
            if not job:
                return bridge_ok({"id":job_id,"status":"unknown","progress":0,"error":None})
            return bridge_ok(job.to_dict())
    def cancel_job(self,job_id:str)->dict:
        """Cancel a generation job."""
        with self._jobs_lock:
            job=self._jobs.get(job_id)
            if not job:return bridge_error("Job not found")
            if job.status not in("pending","generating"):
                return bridge_ok({"message":"Job already finished"})
            job.cancel_requested=True
            job.status="cancelled"
            event=self._cancel_events.get(job_id)
            if event:event.set()
        return bridge_ok({"cancelled":True})
    def cancel_jobs_for_brand(self,brand_slug:str)->dict:
        """Cancel all active jobs for a brand (used on brand switch)."""
        cancelled=[]
        with self._jobs_lock:
            for job in self._jobs.values():
                if job.brand_slug==brand_slug and job.status in("pending","generating"):
                    job.cancel_requested=True
                    job.status="cancelled"
                    event=self._cancel_events.get(job.id)
                    if event:event.set()
                    cancelled.append(job.id)
        return bridge_ok({"cancelled":cancelled})
    def save_image(self,inspiration_id:str,image_idx:int,project_slug:str|None=None)->dict:
        """Save an inspiration image to assets."""
        slug=get_active_brand()
        if not slug:return bridge_error("No brand selected")
        try:
            insp=load_inspiration(slug,inspiration_id)
            if not insp:return bridge_error("Inspiration not found")
            if image_idx<0 or image_idx>=len(insp.images):
                return bridge_error("Invalid image index")
            img=insp.images[image_idx]
            if not img.path or img.status!="ready":
                return bridge_error("Image not available")
            src=Path(img.path)
            if not src.exists():return bridge_error("Image file not found")
            #Determine destination
            brand_dir=get_brand_dir(slug)
            gen_dir=brand_dir/"assets"/"generated"
            gen_dir.mkdir(parents=True,exist_ok=True)
            ts=datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            prefix=f"{project_slug}__" if project_slug else""
            dest=gen_dir/f"{prefix}{ts}_{uuid.uuid4().hex[:6]}.png"
            #Copy file
            import shutil
            shutil.copy2(src,dest)
            #Register in image_status (if service available)
            rel_path=f"generated/{dest.name}"
            #Mark inspiration as saved if all images saved
            insp.status="saved"
            save_inspiration(slug,insp)
            return bridge_ok({"success":True,"saved_path":str(dest),"relative_path":rel_path})
        except Exception as e:
            logger.error(f"save_image error: {e}")
            return bridge_error(str(e))
    def dismiss_inspiration(self,inspiration_id:str)->dict:
        """Dismiss an inspiration (mark for cleanup)."""
        slug=get_active_brand()
        if not slug:return bridge_error("No brand selected")
        try:
            insp=load_inspiration(slug,inspiration_id)
            if not insp:return bridge_error("Inspiration not found")
            insp.status="dismissed"
            save_inspiration(slug,insp)
            return bridge_ok({"success":True})
        except Exception as e:
            logger.error(f"dismiss_inspiration error: {e}")
            return bridge_error(str(e))
    def request_more_like(self,inspiration_id:str)->dict:
        """Request more inspirations similar to one. Returns new job ID."""
        slug=get_active_brand()
        if not slug:return bridge_error("No brand selected")
        #For now, just trigger normal generation
        #Future: pass the inspiration context to the LLM
        return self.trigger_generation(slug)
    def _run_generation(self,job_id:str,brand_slug:str,cancel_event:threading.Event)->None:
        """Background worker for inspiration generation."""
        try:
            with self._jobs_lock:
                job=self._jobs.get(job_id)
                if not job:return
                job.status="generating"
            #Build context and call LLM
            brand_context=self._build_brand_context(brand_slug)
            system_prompt=self._load_system_prompt()
            system_prompt=system_prompt.replace("{brand_context}",brand_context)
            system_prompt=system_prompt.replace("{user_preferences}","")
            #Call LLM for inspiration ideas
            ideas=self._call_llm_for_inspirations(system_prompt,cancel_event)
            if cancel_event.is_set():
                with self._jobs_lock:
                    job=self._jobs.get(job_id)
                    if job:job.status="cancelled"
                return
            if not ideas:
                with self._jobs_lock:
                    job=self._jobs.get(job_id)
                    if job:job.status="failed";job.error="Failed to generate inspirations"
                return
            #Update total
            with self._jobs_lock:
                job=self._jobs.get(job_id)
                if job:job.total_inspirations=len(ideas)
            #Generate images for each inspiration
            brand_dir=get_brand_dir(brand_slug)
            gen_dir=brand_dir/"assets"/"generated"
            gen_dir.mkdir(parents=True,exist_ok=True)
            for idx,idea in enumerate(ideas):
                if cancel_event.is_set():break
                insp=self._create_inspiration_from_idea(idea)
                save_inspiration(brand_slug,insp)
                #Generate images
                self._generate_images_for_inspiration(brand_slug,insp,gen_dir,cancel_event)
                with self._jobs_lock:
                    job=self._jobs.get(job_id)
                    if job:
                        job.inspirations_completed=idx+1
                        job.progress=(idx+1)/len(ideas)
            #Update meta
            meta=load_inspiration_meta(brand_slug)
            meta.last_generated_at=datetime.utcnow().isoformat()
            save_inspiration_meta(brand_slug,meta)
            with self._jobs_lock:
                job=self._jobs.get(job_id)
                if job and job.status=="generating":
                    job.status="completed"
                    job.progress=1.0
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            with self._jobs_lock:
                job=self._jobs.get(job_id)
                if job:job.status="failed";job.error=str(e)
    def _call_llm_for_inspirations(self,system_prompt:str,cancel_event:threading.Event)->list[InspirationIdea]|None:
        """Call LLM to generate inspiration ideas."""
        try:
            settings=get_settings()
            if not settings.openai_api_key:
                logger.error("OpenAI API key not configured")
                return None
            import openai
            client=openai.OpenAI(api_key=settings.openai_api_key)
            if cancel_event.is_set():return None
            #Use structured output
            response=client.beta.chat.completions.parse(
                model="gpt-4o-mini",
                messages=[
                    {"role":"system","content":system_prompt},
                    {"role":"user","content":"Generate 2-3 creative inspirations for this brand."}
                ],
                response_format=InspirationBatch
            )
            if cancel_event.is_set():return None
            parsed=response.choices[0].message.parsed
            if parsed:return parsed.inspirations
            return None
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return None
    def _create_inspiration_from_idea(self,idea:InspirationIdea)->Inspiration:
        """Create an Inspiration record from an LLM idea."""
        images=[InspirationImage(prompt=p.description,status="generating")for p in idea.image_prompts]
        return Inspiration(title=idea.title,rationale=idea.rationale,target_channel=idea.target_channel,images=images,project_slug=idea.project_slug,product_slugs=idea.product_slugs,status="generating")
    def _generate_images_for_inspiration(self,brand_slug:str,insp:Inspiration,output_dir:Path,cancel_event:threading.Event)->None:
        """Generate images for an inspiration using Gemini."""
        settings=get_settings()
        if not settings.gemini_api_key:
            logger.error("Gemini API key not configured")
            for img in insp.images:
                img.status="failed"
                img.error="Gemini API key not configured"
            save_inspiration(brand_slug,insp)
            return
        from google import genai
        from google.genai import types
        client=genai.Client(api_key=settings.gemini_api_key,vertexai=False)
        for idx,img in enumerate(insp.images):
            if cancel_event.is_set():break
            try:
                prompt=img.prompt
                response=client.models.generate_content(
                    model="gemini-2.0-flash-preview-image-generation",
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_modalities=["IMAGE"],
                        image_config=types.ImageConfig(aspect_ratio="1:1",image_size="1024x1024")
                    )
                )
                #Extract image
                for part in response.parts:
                    if part.inline_data:
                        image=part.as_image()
                        ts=datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                        filename=f"inspiration__{insp.id}_{idx}_{ts}.png"
                        img_path=output_dir/filename
                        image.save(str(img_path))
                        #Generate thumbnail
                        thumb_path=output_dir/f"inspiration__{insp.id}_{idx}_{ts}_thumb.jpg"
                        self._generate_thumbnail(img_path,thumb_path)
                        img.path=str(img_path)
                        img.thumbnail_path=str(thumb_path)
                        img.generated_at=datetime.utcnow().isoformat()
                        img.status="ready"
                        break
                else:
                    img.status="failed"
                    img.error="No image in response"
            except Exception as e:
                logger.error(f"Image generation failed for {insp.id}[{idx}]: {e}")
                img.status="failed"
                img.error=str(e)
            save_inspiration(brand_slug,insp)
        #Update inspiration status
        ready_count=sum(1 for i in insp.images if i.status=="ready")
        if ready_count>0:insp.status="ready"
        else:insp.status="failed"
        save_inspiration(brand_slug,insp)
    def _generate_thumbnail(self,src_path:Path,thumb_path:Path,size:tuple[int,int]=(256,256))->None:
        """Generate a thumbnail for an image."""
        try:
            with Image.open(src_path) as img:
                img.thumbnail(size,Image.Resampling.LANCZOS)
                img=img.convert("RGB")
                img.save(thumb_path,"JPEG",quality=85)
        except Exception as e:
            logger.warning(f"Thumbnail generation failed: {e}")
