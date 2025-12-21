"""API key configuration storage."""
import json,os
from pathlib import Path
#Config file for persistent settings (API keys, preferences)
CONFIG_PATH=Path.home()/".sip-videogen"/"config.json"
def _load_config()->dict:
    """Load config from disk."""
    if CONFIG_PATH.exists():
        try:return json.loads(CONFIG_PATH.read_text())
        except(json.JSONDecodeError,OSError):pass
    return{}
def _save_config(config:dict)->None:
    """Save config to disk."""
    CONFIG_PATH.parent.mkdir(parents=True,exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(config,indent=2))
def load_api_keys_from_config()->None:
    """Load API keys from config into environment (called on startup)."""
    c=_load_config();keys=c.get("api_keys",{})
    if keys.get("openai")and not os.environ.get("OPENAI_API_KEY"):os.environ["OPENAI_API_KEY"]=keys["openai"]
    if keys.get("gemini")and not os.environ.get("GEMINI_API_KEY"):os.environ["GEMINI_API_KEY"]=keys["gemini"]
def save_api_keys(openai_key:str,gemini_key:str)->None:
    """Save API keys to environment and persist to config file."""
    if openai_key:os.environ["OPENAI_API_KEY"]=openai_key
    if gemini_key:os.environ["GEMINI_API_KEY"]=gemini_key
    c=_load_config()
    c["api_keys"]={"openai":openai_key or c.get("api_keys",{}).get("openai",""),"gemini":gemini_key or c.get("api_keys",{}).get("gemini","")}
    _save_config(c)
def check_api_keys()->dict[str,bool]:
    """Check if required API keys are configured."""
    o=bool(os.environ.get("OPENAI_API_KEY"));g=bool(os.environ.get("GEMINI_API_KEY"))
    return{"openai":o,"gemini":g,"all_configured":o and g}
