"""User preference memory for inspiration generation.
This module tracks user feedback (saves, dismisses, more-like-this) and uses
LLM analysis to extract preference patterns for better inspiration generation.
Storage: ~/.sip-videogen/brands/{slug}/inspiration_preferences.json"""
from __future__ import annotations
import json,logging
from datetime import datetime
from pathlib import Path
from typing import List,Literal
from pydantic import BaseModel,Field
from .storage import get_brand_dir
from ..utils.file_utils import write_atomically
from ..config.settings import get_settings
logger=logging.getLogger(__name__)
#Models
class InspirationFeedback(BaseModel):
    """Single feedback entry for an inspiration."""
    inspiration_id:str
    action:Literal["saved","dismissed","more_like_this"]
    title:str
    rationale:str
    target_channel:str
    timestamp:str=Field(default_factory=lambda:datetime.utcnow().isoformat())
class InspirationPreferences(BaseModel):
    """User preferences derived from inspiration feedback."""
    feedback_history:List[InspirationFeedback]=Field(default_factory=list,description="Last 50 feedback entries")
    learned_summary:str|None=Field(default=None,description="LLM-generated preference summary (max 150 tokens)")
    sample_count:int=Field(default=0,description="Total feedback samples collected")
    samples_since_last_analysis:int=Field(default=0,description="Samples since last LLM analysis")
    last_analysis:str|None=Field(default=None,description="ISO timestamp of last analysis")
#Storage paths
def _get_preferences_path(brand_slug:str)->Path:
    """Get the preferences file path for a brand."""
    return get_brand_dir(brand_slug)/"inspiration_preferences.json"
def load_preferences(brand_slug:str)->InspirationPreferences:
    """Load preferences for a brand."""
    p=_get_preferences_path(brand_slug)
    if not p.exists():return InspirationPreferences()
    try:
        data=json.loads(p.read_text())
        return InspirationPreferences.model_validate(data)
    except Exception as e:
        logger.error(f"Failed to load preferences for {brand_slug}: {e}")
        return InspirationPreferences()
def save_preferences(brand_slug:str,prefs:InspirationPreferences)->None:
    """Save preferences atomically."""
    p=_get_preferences_path(brand_slug)
    p.parent.mkdir(parents=True,exist_ok=True)
    write_atomically(p,prefs.model_dump_json(indent=2))
def record_feedback(brand_slug:str,inspiration_id:str,action:str,title:str,rationale:str,target_channel:str)->None:
    """Record user feedback on an inspiration."""
    prefs=load_preferences(brand_slug)
    fb=InspirationFeedback(inspiration_id=inspiration_id,action=action,title=title,rationale=rationale,target_channel=target_channel)
    prefs.feedback_history.append(fb)
    #Keep only last 50 entries
    if len(prefs.feedback_history)>50:prefs.feedback_history=prefs.feedback_history[-50:]
    prefs.sample_count+=1
    prefs.samples_since_last_analysis+=1
    save_preferences(brand_slug,prefs)
def get_preference_summary(brand_slug:str)->str|None:
    """Get the learned preference summary for a brand."""
    prefs=load_preferences(brand_slug)
    return prefs.learned_summary
def should_analyze(brand_slug:str)->bool:
    """Check if we should run preference analysis."""
    prefs=load_preferences(brand_slug)
    #Need at least 10 samples
    if prefs.sample_count<10:return False
    #Need at least 5 new samples since last analysis
    if prefs.samples_since_last_analysis<5:return False
    #Rate limit: max once per 24 hours
    if prefs.last_analysis:
        try:
            last=datetime.fromisoformat(prefs.last_analysis.replace("Z","+00:00"))
            hours=(datetime.utcnow()-last.replace(tzinfo=None)).total_seconds()/3600
            if hours<24:return False
        except:pass
    return True
def run_analysis(brand_slug:str)->str|None:
    """Run LLM analysis to extract preference patterns.
    Returns the learned summary or None on failure."""
    prefs=load_preferences(brand_slug)
    if not prefs.feedback_history:return None
    #Build prompt with recent feedback
    recent=prefs.feedback_history[-20:]#Last 20 entries
    fb_text="\n".join([f"- [{fb.action.upper()}] '{fb.title}' ({fb.target_channel}): {fb.rationale[:100]}"for fb in recent])
    prompt=f"""Analyze these user feedback patterns for brand imagery:
{fb_text}

Based on SAVED items (user liked) vs DISMISSED items (user didn't like), summarize in 2-3 sentences:
1. What visual styles/themes does the user prefer?
2. What channels or content types resonate most?
3. Any patterns to avoid?

Keep the summary under 100 words. Be specific and actionable for future image generation."""
    try:
        settings=get_settings()
        if not settings.openai_api_key:
            logger.warning("OpenAI API key not set, skipping preference analysis")
            return None
        import openai
        client=openai.OpenAI(api_key=settings.openai_api_key)
        response=client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role":"system","content":"You are a creative director analyzing user preferences for brand imagery."},
                {"role":"user","content":prompt}
            ],
            max_tokens=200
        )
        summary=response.choices[0].message.content.strip()
        #Update preferences with new summary
        prefs.learned_summary=summary
        prefs.samples_since_last_analysis=0
        prefs.last_analysis=datetime.utcnow().isoformat()
        save_preferences(brand_slug,prefs)
        logger.info(f"Updated preference summary for {brand_slug}")
        return summary
    except Exception as e:
        logger.error(f"Preference analysis failed for {brand_slug}: {e}")
        return None
