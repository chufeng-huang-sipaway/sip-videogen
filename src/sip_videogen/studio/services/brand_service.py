"""Brand management service."""
from __future__ import annotations

import asyncio
import base64
import logging
from datetime import datetime
from pathlib import Path

from sip_videogen.brands.models import (
    AudienceProfile,
    BrandCoreIdentity,
    BrandIndexEntry,
    CompetitivePositioning,
    VisualIdentity,
    VoiceGuidelines,
)
from sip_videogen.brands.storage import (
    backup_brand_identity,
    get_active_brand,
    get_brand_dir,
    list_brand_backups,
    list_brands,
    load_brand,
    load_brand_summary,
    restore_brand_backup,
    save_brand,
    set_active_brand,
)
from sip_videogen.brands.storage import create_brand as storage_create_brand
from sip_videogen.brands.storage import delete_brand as storage_delete_brand

from ..state import BridgeState
from ..utils.bridge_types import ALLOWED_IMAGE_EXTS, ALLOWED_TEXT_EXTS, BridgeResponse

logger=logging.getLogger(__name__)
class BrandService:
    """Brand CRUD and identity management."""
    def __init__(self,state:BridgeState):self._state=state
    def get_brands(self)->dict:
        """Get list of all available brands."""
        try:
            self._sync_brand_index()
            entries=list_brands();brands=[{"slug":e.slug,"name":e.name,"category":e.category}for e in entries]
            active=get_active_brand()
            logger.info("Found %d brands: %s",len(brands),[b['slug']for b in brands])
            logger.info("Active brand: %s",active)
            return BridgeResponse(success=True,data={"brands":brands,"active":active}).to_dict()
        except Exception as e:
            logger.exception("Error getting brands: %s",e)
            return BridgeResponse(success=False,error=str(e)).to_dict()
    def _sync_brand_index(self)->None:
        """Sync index.json with actual brand directories on disk."""
        from sip_videogen.brands.storage import get_brands_dir, load_index, save_index
        try:
            brands_dir=get_brands_dir()
            if not brands_dir.exists():return
            index=load_index();changed=False;valid_entries=[]
            for entry in index.brands:
                brand_dir=brands_dir/entry.slug
                if brand_dir.exists()and(brand_dir/"identity.json").exists():valid_entries.append(entry)
                else:logger.info("Removing orphaned entry: %s",entry.slug);changed=True
            for item in brands_dir.iterdir():
                if not item.is_dir()or item.name.startswith("."):continue
                if item.name not in[e.slug for e in valid_entries]:
                    summary=load_brand_summary(item.name)
                    if summary:
                        logger.info("Adding missing entry: %s",item.name)
                        entry=BrandIndexEntry(slug=summary.slug,name=summary.name,category=summary.category,created_at=datetime.utcnow(),updated_at=datetime.utcnow())
                        valid_entries.append(entry);changed=True
            if changed:
                index.brands=valid_entries
                if index.active_brand and index.active_brand not in[e.slug for e in valid_entries]:
                    logger.info("Clearing invalid active brand: %s",index.active_brand)
                    index.active_brand=valid_entries[0].slug if valid_entries else None
                save_index(index);logger.info("Index updated with %d brands",len(valid_entries))
        except Exception as e:logger.error("Error syncing index: %s",e)
    def set_brand(self,slug:str)->dict:
        """Set the active brand and initialize advisor."""
        from sip_videogen.advisor.agent import BrandAdvisor
        try:
            entries=list_brands()
            if slug not in[e.slug for e in entries]:return BridgeResponse(success=False,error=f"Brand '{slug}' not found").to_dict()
            set_active_brand(slug)
            if self._state.advisor is None:self._state.advisor=BrandAdvisor(brand_slug=slug,progress_callback=self._get_progress_callback())
            else:self._state.advisor.set_brand(slug,preserve_history=False)
            return BridgeResponse(success=True,data={"slug":slug}).to_dict()
        except Exception as e:return BridgeResponse(success=False,error=str(e)).to_dict()
    def _get_progress_callback(self):
        """Get progress callback function for advisor."""
        import time
        def callback(progress):
            event={"type":progress.event_type,"timestamp":int(time.time()*1000),"message":progress.message,"detail":progress.detail or""}
            self._state.execution_trace.append(event)
            if progress.event_type=="skill_loaded":
                skill_name=progress.message.replace("Loading ","").replace(" skill","")
                if skill_name not in self._state.matched_skills:self._state.matched_skills.append(skill_name)
            if progress.event_type=="tool_end":self._state.current_progress="";self._state.current_progress_type=""
            else:self._state.current_progress=progress.message;self._state.current_progress_type=progress.event_type
        return callback
    def get_brand_info(self,slug:str|None=None)->dict:
        """Get detailed brand information."""
        try:
            target_slug=slug or get_active_brand()
            if not target_slug:return BridgeResponse(success=False,error="No brand selected").to_dict()
            summary=load_brand_summary(target_slug)
            if not summary:return BridgeResponse(success=False,error=f"Brand '{target_slug}' not found").to_dict()
            return BridgeResponse(success=True,data={"slug":target_slug,"name":summary.name,"tagline":summary.tagline,"category":summary.category}).to_dict()
        except Exception as e:return BridgeResponse(success=False,error=str(e)).to_dict()
    def get_brand_identity(self)->dict:
        """Get full brand identity (L1 data) for the active brand."""
        try:
            slug=get_active_brand()
            if not slug:return BridgeResponse(success=False,error="No brand selected").to_dict()
            identity=load_brand(slug)
            if not identity:return BridgeResponse(success=False,error=f"Brand '{slug}' not found").to_dict()
            return BridgeResponse(success=True,data=identity.model_dump(mode="json")).to_dict()
        except Exception as e:return BridgeResponse(success=False,error=str(e)).to_dict()
    def update_brand_identity_section(self,section:str,data:dict)->dict:
        """Update a specific section of the brand identity."""
        try:
            slug=get_active_brand()
            if not slug:return BridgeResponse(success=False,error="No brand selected").to_dict()
            identity=load_brand(slug)
            if not identity:return BridgeResponse(success=False,error=f"Brand '{slug}' not found").to_dict()
            valid_sections={"core","visual","voice","audience","positioning","constraints_avoid"}
            if section not in valid_sections:return BridgeResponse(success=False,error=f"Invalid section: {section}. Must be one of: {', '.join(sorted(valid_sections))}").to_dict()
            try:
                if section=="core":identity.core=BrandCoreIdentity.model_validate(data)
                elif section=="visual":identity.visual=VisualIdentity.model_validate(data)
                elif section=="voice":identity.voice=VoiceGuidelines.model_validate(data)
                elif section=="audience":identity.audience=AudienceProfile.model_validate(data)
                elif section=="positioning":identity.positioning=CompetitivePositioning.model_validate(data)
                elif section=="constraints_avoid":
                    if not isinstance(data,dict):return BridgeResponse(success=False,error="constraints_avoid section must be an object with 'constraints' and 'avoid' arrays").to_dict()
                    constraints=data.get("constraints",[]);avoid=data.get("avoid",[])
                    if not isinstance(constraints,list)or not isinstance(avoid,list):return BridgeResponse(success=False,error="'constraints' and 'avoid' must be arrays").to_dict()
                    identity.constraints=constraints;identity.avoid=avoid
            except Exception as ve:return BridgeResponse(success=False,error=f"Invalid {section} data: {ve}").to_dict()
            save_brand(identity)
            if self._state.advisor:self._state.advisor.set_brand(slug,preserve_history=True)
            return BridgeResponse(success=True,data=identity.model_dump(mode="json")).to_dict()
        except Exception as e:return BridgeResponse(success=False,error=str(e)).to_dict()
    def regenerate_brand_identity(self,confirm:bool)->dict:
        """Regenerate brand identity from source materials."""
        from sip_videogen.agents.brand_director import develop_brand_with_output
        try:
            if not confirm:return BridgeResponse(success=False,error="Regeneration requires confirm=True. This will overwrite the current identity.").to_dict()
            slug=get_active_brand()
            if not slug:return BridgeResponse(success=False,error="No brand selected").to_dict()
            identity=load_brand(slug)
            if not identity:return BridgeResponse(success=False,error=f"Brand '{slug}' not found").to_dict()
            brand_dir=get_brand_dir(slug);docs_dir=brand_dir/"docs"
            if not docs_dir.exists()or not any(docs_dir.iterdir()):return BridgeResponse(success=False,error="No source documents found. Add documents to the brand's docs/ folder before regenerating.").to_dict()
            concept_parts=[]
            for doc_path in sorted(docs_dir.rglob("*")):
                if not doc_path.is_file()or doc_path.name.startswith(".")or doc_path.suffix.lower()not in ALLOWED_TEXT_EXTS:continue
                try:
                    content=doc_path.read_text(encoding="utf-8",errors="replace")
                    if len(content)>50*1024:content=content[:50*1024]+"\n...[truncated]"
                    concept_parts.append(f"## From: {doc_path.name}\n\n{content}")
                except Exception:continue
            if not concept_parts:return BridgeResponse(success=False,error="No readable documents found in docs/ folder.").to_dict()
            concept="\n\n---\n\n".join(concept_parts)
            if len(concept)>4800:concept=concept[:4800]+"\n...[truncated]"
            try:backup_filename=backup_brand_identity(slug);logger.info("Backed up identity to: %s",backup_filename)
            except Exception as be:return BridgeResponse(success=False,error=f"Failed to backup current identity: {be}").to_dict()
            logger.info("Starting regeneration for %s...",slug)
            output=asyncio.run(develop_brand_with_output(concept,existing_brand_slug=slug))
            new_identity=output.brand_identity;new_identity.slug=slug
            logger.info("AI completed! Brand name: %s",new_identity.core.name)
            save_brand(new_identity)
            if self._state.advisor:self._state.advisor.set_brand(slug,preserve_history=True)
            return BridgeResponse(success=True,data=new_identity.model_dump(mode="json")).to_dict()
        except Exception as e:
            logger.exception("Regeneration error: %s",e)
            return BridgeResponse(success=False,error=str(e)).to_dict()
    def list_identity_backups(self)->dict:
        """List all identity backups for the active brand."""
        try:
            slug=get_active_brand()
            if not slug:return BridgeResponse(success=False,error="No brand selected").to_dict()
            backups=list_brand_backups(slug)
            return BridgeResponse(success=True,data={"backups":backups}).to_dict()
        except Exception as e:return BridgeResponse(success=False,error=str(e)).to_dict()
    def restore_identity_backup(self,filename:str)->dict:
        """Restore brand identity from a backup file."""
        try:
            slug=get_active_brand()
            if not slug:return BridgeResponse(success=False,error="No brand selected").to_dict()
            if "/"in filename or"\\"in filename:return BridgeResponse(success=False,error="Invalid filename: path separators not allowed").to_dict()
            if not filename.endswith(".json"):return BridgeResponse(success=False,error="Invalid filename: must end with .json").to_dict()
            try:restored_identity=restore_brand_backup(slug,filename)
            except ValueError as e:return BridgeResponse(success=False,error=str(e)).to_dict()
            restored_identity.slug=slug;save_brand(restored_identity)
            logger.info("Restored identity from backup: %s",filename)
            if self._state.advisor:self._state.advisor.set_brand(slug,preserve_history=True)
            return BridgeResponse(success=True,data=restored_identity.model_dump(mode="json")).to_dict()
        except Exception as e:
            logger.exception("Restore identity error: %s",e)
            return BridgeResponse(success=False,error=str(e)).to_dict()
    def delete_brand(self,slug:str)->dict:
        """Delete a brand and all its files."""
        try:
            entries=list_brands()
            if slug not in[e.slug for e in entries]:return BridgeResponse(success=False,error=f"Brand '{slug}' not found").to_dict()
            if self._state.get_active_slug()==slug:self._state.advisor=None
            if get_active_brand()==slug:set_active_brand(None)
            deleted=storage_delete_brand(slug)
            if not deleted:return BridgeResponse(success=False,error=f"Failed to delete brand '{slug}'").to_dict()
            return BridgeResponse(success=True).to_dict()
        except Exception as e:return BridgeResponse(success=False,error=str(e)).to_dict()
    def create_brand_from_materials(self,description:str,images:list[dict],documents:list[dict])->dict:
        """Create a new brand using AI agents with user-provided materials."""
        from sip_videogen.agents.brand_director import develop_brand_with_output
        logger.info("Starting brand creation - desc:%d chars, images:%d, docs:%d",len(description),len(images),len(documents))
        try:
            concept_parts=[]
            if description.strip():concept_parts.append(f"## Brand Description\n\n{description.strip()}");logger.debug("Added description to concept")
            for doc in documents:
                filename=doc.get("filename","unknown");data_b64=doc.get("data","")
                try:
                    content=base64.b64decode(data_b64).decode("utf-8",errors="replace")
                    logger.debug("Extracted %d chars from %s",len(content),filename)
                    if len(content)>50*1024:content=content[:50*1024]+"\n...[truncated]";logger.debug("Truncated to 50KB")
                    concept_parts.append(f"## From: {filename}\n\n{content}")
                except Exception as e:logger.error("Error reading %s: %s",filename,e)
            if not concept_parts:logger.error("No concept parts");return BridgeResponse(success=False,error="Please provide a description or upload documents.").to_dict()
            concept="\n\n---\n\n".join(concept_parts)
            logger.debug("Combined concept length: %d chars",len(concept))
            max_concept_len=4800
            if len(concept)>max_concept_len:
                logger.debug("Concept too long (%d), truncating...",len(concept))
                if description.strip():
                    desc_part=f"## Brand Description\n\n{description.strip()}";remaining=max_concept_len-len(desc_part)-100
                    if remaining>500:doc_summary=concept[len(desc_part):][:remaining];concept=desc_part+"\n\n---\n\n"+doc_summary+"\n...[truncated]"
                    else:concept=desc_part[:max_concept_len]
                else:concept=concept[:max_concept_len]+"\n...[truncated]"
                logger.debug("Final concept length: %d chars",len(concept))
            self._state.current_progress="Creating brand identity..."
            logger.info("Calling AI brand director...")
            output=asyncio.run(develop_brand_with_output(concept))
            brand_identity=output.brand_identity
            logger.info("AI completed! Brand name: %s",brand_identity.core.name)
            self._state.current_progress="Saving brand..."
            storage_create_brand(brand_identity)
            slug=brand_identity.slug
            brand_dir=get_brand_dir(slug);assets_dir=brand_dir/"assets";docs_dir=brand_dir/"docs"
            logger.debug("Saving %d images...",len(images))
            for img in images:
                filename=img.get("filename","");data_b64=img.get("data","")
                if not filename or not data_b64:continue
                ext=Path(filename).suffix.lower()
                if ext not in ALLOWED_IMAGE_EXTS:logger.debug("Skipping %s (unsupported ext)",filename);continue
                category="logo"if"logo"in filename.lower()else"marketing"
                target_dir=assets_dir/category;target_dir.mkdir(parents=True,exist_ok=True)
                target_path=target_dir/filename
                if not target_path.exists():target_path.write_bytes(base64.b64decode(data_b64));logger.debug("Saved: %s/%s",category,filename)
            logger.debug("Saving %d documents...",len(documents))
            docs_dir.mkdir(parents=True,exist_ok=True)
            for doc in documents:
                filename=doc.get("filename","");data_b64=doc.get("data","")
                if not filename or not data_b64:continue
                ext=Path(filename).suffix.lower()
                if ext not in ALLOWED_TEXT_EXTS:logger.debug("Skipping %s (unsupported ext)",filename);continue
                target_path=docs_dir/filename
                if not target_path.exists():target_path.write_bytes(base64.b64decode(data_b64));logger.debug("Saved: docs/%s",filename)
            self._state.current_progress=""
            logger.info("SUCCESS! Brand '%s' created",brand_identity.core.name)
            return BridgeResponse(success=True,data={"slug":slug,"name":brand_identity.core.name}).to_dict()
        except ValueError as e:logger.error("ValueError: %s",e);return BridgeResponse(success=False,error=str(e)).to_dict()
        except Exception as e:
            logger.exception("Exception during brand creation: %s",e)
            self._state.current_progress=""
            return BridgeResponse(success=False,error=f"Failed to create brand: {e}").to_dict()
