"""Data models and storage for brand inspirations.
This module defines the inspiration models for proactive creative ideas:
- InspirationImagePrompt: LLM output schema for image prompts
- InspirationIdea: LLM output schema for a single inspiration
- InspirationBatch: LLM output schema for inspiration generation
- InspirationImage: Stored image metadata
- Inspiration: Stored inspiration with images
- InspirationJob: Job tracking for generation
- InspirationIndex: Registry of inspirations per brand
Storage functions mirror the storage.py pattern."""
from __future__ import annotations
import json,logging,threading,uuid
from datetime import datetime
from pathlib import Path
from typing import Literal,List
from pydantic import BaseModel,Field
from .storage import get_brand_dir
from ..utils.file_utils import write_atomically
logger=logging.getLogger(__name__)
#Per-brand locks for thread-safe index operations
_brand_locks:dict[str,threading.Lock]={}
_brand_locks_lock=threading.Lock()
def _get_brand_lock(brand_slug:str)->threading.Lock:
    """Get or create a lock for a brand's inspiration index operations."""
    with _brand_locks_lock:
        if brand_slug not in _brand_locks:_brand_locks[brand_slug]=threading.Lock()
        return _brand_locks[brand_slug]
#LLM Output Models (structured output from openai.beta.chat.completions.parse)
class InspirationImagePrompt(BaseModel):
    """LLM output schema for a single image prompt."""
    description:str=Field(...,description="Detailed prompt for image generation")
    style_notes:str=Field(default="",description="Visual style guidance")
class InspirationIdea(BaseModel):
    """LLM output schema for a single inspiration."""
    title:str=Field(...,min_length=1,max_length=100,description="Inspiration title")
    rationale:str=Field(...,min_length=10,max_length=500,description="Why this idea fits the brand")
    target_channel:Literal["instagram","website","email","general"]=Field(default="general",description="Target platform")
    product_slugs:List[str]=Field(default_factory=list,description="Related product slugs")
    project_slug:str|None=Field(default=None,description="Related project slug")
    image_prompts:List[InspirationImagePrompt]=Field(...,min_length=3,max_length=3,description="Exactly 3 image prompts")
class InspirationBatch(BaseModel):
    """LLM output schema for inspiration generation."""
    inspirations:List[InspirationIdea]=Field(...,min_length=2,max_length=3,description="2-3 inspirations")
#Storage Models
class InspirationImage(BaseModel):
    """Stored image metadata."""
    path:str|None=Field(default=None,description="Full image path (None if failed)")
    thumbnail_path:str|None=Field(default=None,description="Thumbnail path (None if failed)")
    prompt:str=Field(default="",description="Generation prompt used")
    generated_at:str=Field(default="",description="ISO timestamp of generation")
    status:Literal["generating","ready","failed"]=Field(default="generating")
    error:str|None=Field(default=None,description="Error message if failed")
class Inspiration(BaseModel):
    """Stored inspiration with images."""
    id:str=Field(default_factory=lambda:uuid.uuid4().hex[:12],description="Unique ID")
    title:str=Field(default="",description="Inspiration title")
    rationale:str=Field(default="",description="Why this idea fits the brand")
    target_channel:str=Field(default="general",description="Target platform")
    images:List[InspirationImage]=Field(default_factory=list,description="Generated images")
    project_slug:str|None=Field(default=None,description="Related project slug")
    product_slugs:List[str]=Field(default_factory=list,description="Related product slugs")
    created_at:str=Field(default_factory=lambda:datetime.utcnow().isoformat(),description="Creation timestamp")
    status:Literal["generating","ready","saved","dismissed","failed"]=Field(default="generating")
    def to_dict(self)->dict:
        """Convert to dict for JSON serialization with camelCase keys for frontend."""
        return {"id":self.id,"title":self.title,"rationale":self.rationale,"targetChannel":self.target_channel,
            "images":[{"path":img.path,"thumbnailPath":img.thumbnail_path,"prompt":img.prompt,
                "generatedAt":img.generated_at,"status":img.status,"error":img.error} for img in self.images],
            "projectSlug":self.project_slug,"productSlugs":self.product_slugs,"createdAt":self.created_at,"status":self.status}
class InspirationJob(BaseModel):
    """Job tracking for inspiration generation."""
    id:str=Field(default_factory=lambda:uuid.uuid4().hex[:12],description="Job ID")
    brand_slug:str=Field(default="",description="Brand slug")
    status:Literal["pending","generating","completed","failed","cancelled"]=Field(default="pending")
    progress:float=Field(default=0.0,ge=0.0,le=1.0,description="Progress 0.0-1.0")
    inspirations_completed:int=Field(default=0,description="Completed inspiration count")
    total_inspirations:int=Field(default=0,description="Total inspiration count")
    error:str|None=Field(default=None,description="Error message if failed")
    created_at:str=Field(default_factory=lambda:datetime.utcnow().isoformat())
    cancel_requested:bool=Field(default=False,description="Cancellation requested")
    def to_dict(self)->dict:
        """Convert to dict for JSON serialization with camelCase keys for frontend."""
        return {"id":self.id,"brandSlug":self.brand_slug,"status":self.status,"progress":self.progress,
            "inspirationsCompleted":self.inspirations_completed,"totalInspirations":self.total_inspirations,
            "error":self.error,"createdAt":self.created_at}
class InspirationMeta(BaseModel):
    """Metadata for inspiration storage per brand."""
    version:str=Field(default="1.0")
    last_generated_at:str|None=Field(default=None,description="Last auto-generation timestamp")
    inspiration_ids:List[str]=Field(default_factory=list,description="List of inspiration IDs")
class InspirationIndex(BaseModel):
    """Registry of inspirations for a brand."""
    version:str=Field(default="1.0")
    inspirations:List[Inspiration]=Field(default_factory=list)
    def get_inspiration(self,id:str)->Inspiration|None:
        for i in self.inspirations:
            if i.id==id:return i
        return None
    def add_inspiration(self,entry:Inspiration)->None:
        self.inspirations=[i for i in self.inspirations if i.id!=entry.id]
        self.inspirations.append(entry)
    def remove_inspiration(self,id:str)->bool:
        n=len(self.inspirations)
        self.inspirations=[i for i in self.inspirations if i.id!=id]
        return len(self.inspirations)<n
#Storage Functions
def get_inspirations_dir(brand_slug:str)->Path:
    """Get the inspirations directory for a brand."""
    return get_brand_dir(brand_slug)/"inspirations"
def get_inspiration_index_path(brand_slug:str)->Path:
    """Get the index.json path for a brand's inspirations."""
    return get_inspirations_dir(brand_slug)/"index.json"
def get_inspiration_meta_path(brand_slug:str)->Path:
    """Get the meta.json path for a brand's inspirations."""
    return get_inspirations_dir(brand_slug)/"meta.json"
def get_inspiration_path(brand_slug:str,inspiration_id:str)->Path:
    """Get the path to a specific inspiration JSON file."""
    return get_inspirations_dir(brand_slug)/f"{inspiration_id}.json"
def _ensure_inspirations_dir(brand_slug:str)->Path:
    """Ensure the inspirations directory exists."""
    d=get_inspirations_dir(brand_slug)
    d.mkdir(parents=True,exist_ok=True)
    return d
def load_inspiration_index(brand_slug:str)->InspirationIndex:
    """Load the inspiration index for a brand."""
    p=get_inspiration_index_path(brand_slug)
    if not p.exists():return InspirationIndex()
    try:
        data=json.loads(p.read_text())
        return InspirationIndex.model_validate(data)
    except Exception as e:
        logger.error(f"Failed to load inspiration index for {brand_slug}: {e}")
        return InspirationIndex()
def save_inspiration_index(brand_slug:str,index:InspirationIndex)->None:
    """Save the inspiration index atomically."""
    _ensure_inspirations_dir(brand_slug)
    p=get_inspiration_index_path(brand_slug)
    write_atomically(p,index.model_dump_json(indent=2))
def load_inspiration_meta(brand_slug:str)->InspirationMeta:
    """Load the inspiration metadata for a brand."""
    p=get_inspiration_meta_path(brand_slug)
    if not p.exists():return InspirationMeta()
    try:
        data=json.loads(p.read_text())
        return InspirationMeta.model_validate(data)
    except Exception as e:
        logger.error(f"Failed to load inspiration meta for {brand_slug}: {e}")
        return InspirationMeta()
def save_inspiration_meta(brand_slug:str,meta:InspirationMeta)->None:
    """Save the inspiration metadata atomically."""
    _ensure_inspirations_dir(brand_slug)
    p=get_inspiration_meta_path(brand_slug)
    write_atomically(p,meta.model_dump_json(indent=2))
def load_inspiration(brand_slug:str,inspiration_id:str)->Inspiration|None:
    """Load a specific inspiration by ID."""
    p=get_inspiration_path(brand_slug,inspiration_id)
    if not p.exists():return None
    try:
        data=json.loads(p.read_text())
        return Inspiration.model_validate(data)
    except Exception as e:
        logger.error(f"Failed to load inspiration {inspiration_id}: {e}")
        return None
def save_inspiration(brand_slug:str,inspiration:Inspiration)->None:
    """Save an inspiration atomically and update index (thread-safe)."""
    _ensure_inspirations_dir(brand_slug)
    p=get_inspiration_path(brand_slug,inspiration.id)
    write_atomically(p,inspiration.model_dump_json(indent=2))
    #Update index with lock to prevent concurrent read-modify-write corruption
    lock=_get_brand_lock(brand_slug)
    with lock:
        idx=load_inspiration_index(brand_slug)
        idx.add_inspiration(inspiration)
        save_inspiration_index(brand_slug,idx)
def delete_inspiration(brand_slug:str,inspiration_id:str)->bool:
    """Delete an inspiration and update index (thread-safe)."""
    p=get_inspiration_path(brand_slug,inspiration_id)
    if p.exists():p.unlink()
    lock=_get_brand_lock(brand_slug)
    with lock:
        idx=load_inspiration_index(brand_slug)
        removed=idx.remove_inspiration(inspiration_id)
        if removed:save_inspiration_index(brand_slug,idx)
    return removed
def list_inspirations(brand_slug:str,status_filter:str|None=None)->List[Inspiration]:
    """List all inspirations for a brand, optionally filtered by status."""
    idx=load_inspiration_index(brand_slug)
    if status_filter:
        return [i for i in idx.inspirations if i.status==status_filter]
    return idx.inspirations
def cleanup_old_inspirations(brand_slug:str,max_ready:int=20,dismissed_hours:int=24)->int:
    """Clean up old inspirations per retention limits (thread-safe).
    - Max 20 ready/generating inspirations (saved don't count)
    - Dismissed inspirations older than 24 hours are deleted
    Returns number of inspirations deleted."""
    lock=_get_brand_lock(brand_slug)
    now=datetime.utcnow()
    deleted=0
    to_delete_ids=[]
    with lock:
        idx=load_inspiration_index(brand_slug)
        #Identify old dismissed inspirations to delete
        new_list=[]
        for i in idx.inspirations:
            if i.status=="dismissed":
                try:
                    created=datetime.fromisoformat(i.created_at.replace("Z","+00:00"))
                    age_hours=(now-created.replace(tzinfo=None)).total_seconds()/3600
                    if age_hours>dismissed_hours:
                        to_delete_ids.append(i.id)
                        deleted+=1
                        continue
                except:pass
            new_list.append(i)
        idx.inspirations=new_list
        #Enforce max ready/generating limit
        active=[i for i in idx.inspirations if i.status in("ready","generating")]
        if len(active)>max_ready:
            active.sort(key=lambda x:x.created_at)
            to_remove=active[:len(active)-max_ready]
            for i in to_remove:
                to_delete_ids.append(i.id)
                idx.inspirations=[x for x in idx.inspirations if x.id!=i.id]
                deleted+=1
        if deleted>0:save_inspiration_index(brand_slug,idx)
    #Delete files outside of lock (safe, just file deletions)
    for iid in to_delete_ids:
        p=get_inspiration_path(brand_slug,iid)
        if p.exists():p.unlink()
    return deleted
