"""Template CRUD operations."""
from __future__ import annotations
import json
import logging
import shutil
from datetime import datetime
from pathlib import Path
from sip_videogen.constants import ALLOWED_IMAGE_EXTS
from sip_videogen.utils.file_utils import write_atomically
from sip_videogen.exceptions import BrandNotFoundError,TemplateNotFoundError,DuplicateEntityError
from ..models import TemplateFull,TemplateIndex,TemplateSummary
from .base import get_brand_dir
logger=logging.getLogger(__name__)
def get_templates_dir(brand_slug:str)->Path:
    """Get the templates directory for a brand."""
    return get_brand_dir(brand_slug)/"templates"
def get_template_dir(brand_slug:str,template_slug:str)->Path:
    """Get the directory for a specific template."""
    return get_templates_dir(brand_slug)/template_slug
def get_template_index_path(brand_slug:str)->Path:
    """Get the path to the template index file for a brand."""
    return get_templates_dir(brand_slug)/"index.json"
def load_template_index(brand_slug:str)->TemplateIndex:
    """Load the template index for a brand."""
    ip=get_template_index_path(brand_slug)
    if ip.exists():
        try:
            data=json.loads(ip.read_text())
            idx=TemplateIndex.model_validate(data)
            logger.debug("Loaded template index for %s with %d templates",brand_slug,len(idx.templates))
            return idx
        except json.JSONDecodeError as e:logger.warning("Invalid JSON in template index for %s: %s",brand_slug,e)
        except Exception as e:logger.warning("Failed to load template index for %s: %s",brand_slug,e)
    logger.debug("Creating new template index for %s",brand_slug)
    return TemplateIndex()
def save_template_index(brand_slug:str,index:TemplateIndex)->None:
    """Save the template index for a brand atomically."""
    ip=get_template_index_path(brand_slug)
    write_atomically(ip,index.model_dump_json(indent=2))
    logger.debug("Saved template index for %s with %d templates",brand_slug,len(index.templates))
def create_template(brand_slug:str,template:TemplateFull)->TemplateSummary:
    """Create a new template for a brand.
    Args:
        brand_slug: Brand identifier.
        template: Complete template data.
    Returns:
        TemplateSummary extracted from the template.
    Raises:
        BrandNotFoundError: If brand doesn't exist.
        DuplicateEntityError: If template already exists.
    """
    bd=get_brand_dir(brand_slug)
    if not bd.exists():raise BrandNotFoundError(f"Brand '{brand_slug}' not found")
    td=get_template_dir(brand_slug,template.slug)
    if td.exists():raise DuplicateEntityError(f"Template '{template.slug}' already exists in brand '{brand_slug}'")
    #Create directory structure
    td.mkdir(parents=True,exist_ok=True)
    (td/"images").mkdir(exist_ok=True)
    #Save template files atomically
    summary=template.to_summary()
    write_atomically(td/"template.json",summary.model_dump_json(indent=2))
    write_atomically(td/"template_full.json",template.model_dump_json(indent=2))
    #Update index
    idx=load_template_index(brand_slug)
    idx.add_template(summary)
    save_template_index(brand_slug,idx)
    logger.info("Created template %s for brand %s",template.slug,brand_slug)
    return summary
def load_template(brand_slug:str,template_slug:str)->TemplateFull|None:
    """Load a template's full details from disk.
    Args:
        brand_slug: Brand identifier.
        template_slug: Template identifier.
    Returns:
        TemplateFull or None if not found.
    """
    td=get_template_dir(brand_slug,template_slug)
    tp=td/"template_full.json"
    if not tp.exists():
        logger.debug("Template not found: %s/%s",brand_slug,template_slug)
        return None
    try:
        data=json.loads(tp.read_text())
        return TemplateFull.model_validate(data)
    except Exception as e:
        logger.error("Failed to load template %s/%s: %s",brand_slug,template_slug,e)
        return None
def load_template_summary(brand_slug:str,template_slug:str)->TemplateSummary|None:
    """Load just the template summary (L0 layer).
    This is faster than load_template() when you only need the summary.
    """
    td=get_template_dir(brand_slug,template_slug)
    sp=td/"template.json"
    if not sp.exists():return None
    try:
        data=json.loads(sp.read_text())
        return TemplateSummary.model_validate(data)
    except Exception as e:
        logger.error("Failed to load template summary %s/%s: %s",brand_slug,template_slug,e)
        return None
def save_template(brand_slug:str,template:TemplateFull)->TemplateSummary:
    """Save/update a template.
    Args:
        brand_slug: Brand identifier.
        template: Updated template data.
    Returns:
        Updated TemplateSummary.
    """
    td=get_template_dir(brand_slug,template.slug)
    if not td.exists():return create_template(brand_slug,template)
    #Update timestamp
    template.updated_at=datetime.utcnow()
    #Save files atomically
    summary=template.to_summary()
    write_atomically(td/"template.json",summary.model_dump_json(indent=2))
    write_atomically(td/"template_full.json",template.model_dump_json(indent=2))
    #Update index
    idx=load_template_index(brand_slug)
    idx.add_template(summary)
    save_template_index(brand_slug,idx)
    logger.info("Saved template %s for brand %s",template.slug,brand_slug)
    return summary
def delete_template(brand_slug:str,template_slug:str)->bool:
    """Delete a template and all its files.
    Returns:
        True if template was deleted, False if not found.
    """
    td=get_template_dir(brand_slug,template_slug)
    if not td.exists():return False
    shutil.rmtree(td)
    #Update index
    idx=load_template_index(brand_slug)
    idx.remove_template(template_slug)
    save_template_index(brand_slug,idx)
    logger.info("Deleted template %s from brand %s",template_slug,brand_slug)
    return True
def list_templates(brand_slug:str)->list[TemplateSummary]:
    """List all templates for a brand, sorted by name."""
    idx=load_template_index(brand_slug)
    return sorted(idx.templates,key=lambda t:t.name.lower())
def list_template_images(brand_slug:str,template_slug:str)->list[str]:
    """List all images for a template.
    Returns:
        List of brand-relative image paths.
    """
    td=get_template_dir(brand_slug,template_slug)
    imd=td/"images"
    if not imd.exists():return[]
    imgs=[]
    for fp in sorted(imd.iterdir()):
        if fp.suffix.lower()in ALLOWED_IMAGE_EXTS:
            imgs.append(f"templates/{template_slug}/images/{fp.name}")
    return imgs
def add_template_image(brand_slug:str,template_slug:str,filename:str,data:bytes)->str:
    """Add an image to a template.
    Args:
        brand_slug: Brand identifier.
        template_slug: Template identifier.
        filename: Image filename.
        data: Image binary data.
    Returns:
        Brand-relative path to the saved image.
    Raises:
        TemplateNotFoundError: If template doesn't exist.
    """
    td=get_template_dir(brand_slug,template_slug)
    if not td.exists():raise TemplateNotFoundError(f"Template '{template_slug}' not found in brand '{brand_slug}'")
    imd=td/"images"
    imd.mkdir(exist_ok=True)
    #Save image
    (imd/filename).write_bytes(data)
    #Return brand-relative path
    br=f"templates/{template_slug}/images/{filename}"
    #Update template's images list
    tmpl=load_template(brand_slug,template_slug)
    if tmpl:
        if br not in tmpl.images:
            tmpl.images.append(br)
            #Set as primary if first image
            if not tmpl.primary_image:tmpl.primary_image=br
            save_template(brand_slug,tmpl)
    logger.info("Added image %s to template %s/%s",filename,brand_slug,template_slug)
    return br
def delete_template_image(brand_slug:str,template_slug:str,filename:str)->bool:
    """Delete an image from a template.
    Returns:
        True if image was deleted, False if not found.
    """
    td=get_template_dir(brand_slug,template_slug)
    ip=td/"images"/filename
    if not ip.exists():return False
    ip.unlink()
    #Update template's images list
    br=f"templates/{template_slug}/images/{filename}"
    tmpl=load_template(brand_slug,template_slug)
    if tmpl:
        if br in tmpl.images:
            tmpl.images.remove(br)
            #Update primary if it was the deleted image
            if tmpl.primary_image==br:tmpl.primary_image=tmpl.images[0]if tmpl.images else""
            save_template(brand_slug,tmpl)
    logger.info("Deleted image %s from template %s/%s",filename,brand_slug,template_slug)
    return True
def set_primary_template_image(brand_slug:str,template_slug:str,brand_relative_path:str)->bool:
    """Set the primary image for a template.
    Args:
        brand_slug: Brand identifier.
        template_slug: Template identifier.
        brand_relative_path: Brand-relative path to the image.
    Returns:
        True if primary was set, False if image not found in template.
    """
    tmpl=load_template(brand_slug,template_slug)
    if not tmpl:return False
    if brand_relative_path not in tmpl.images:return False
    tmpl.primary_image=brand_relative_path
    save_template(brand_slug,tmpl)
    logger.info("Set primary image for template %s/%s to %s",brand_slug,template_slug,brand_relative_path)
    return True
def sync_template_index(brand_slug:str)->int:
    """Reconcile template index with filesystem.
    Adds templates that exist on disk but not in index,
    removes index entries for templates that no longer exist.
    Returns:
        Number of changes made (additions + removals).
    """
    tsd=get_templates_dir(brand_slug)
    if not tsd.exists():return 0
    idx=load_template_index(brand_slug)
    changes=0
    #Find templates on disk
    dslugs=set()
    for item in tsd.iterdir():
        if item.is_dir()and(item/"template_full.json").exists():dslugs.add(item.name)
    #Find templates in index
    islugs={t.slug for t in idx.templates}
    #Add missing to index
    for s in dslugs-islugs:
        tmpl=load_template(brand_slug,s)
        if tmpl:
            idx.add_template(tmpl.to_summary())
            logger.info("Synced template %s to index for brand %s",s,brand_slug)
            changes+=1
    #Remove orphaned from index
    for s in islugs-dslugs:
        idx.remove_template(s)
        logger.info("Removed orphaned template %s from index for brand %s",s,brand_slug)
        changes+=1
    if changes>0:save_template_index(brand_slug,idx)
    return changes
