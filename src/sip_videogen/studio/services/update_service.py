"""App update management service."""
from __future__ import annotations
import asyncio,sys,threading
from sip_videogen.studio import __version__
from sip_videogen.studio.updater import(DownloadProgress,UpdateInfo,check_for_updates as do_check,download_update,get_current_version,get_update_settings,install_update,is_bundled_app,mark_update_checked,save_update_settings)
from ..state import BridgeState
from ..utils.bridge_types import bridge_ok,bridge_error
class UpdateService:
    """App update checking and installation."""
    def __init__(self,state:BridgeState):self._state=state
    def get_app_version(self)->dict:
        """Get the current app version."""
        return bridge_ok({"version":__version__,"is_bundled":is_bundled_app()})
    def check_for_updates(self)->dict:
        """Check if a newer version is available on GitHub Releases."""
        try:
            update_info=asyncio.run(do_check());mark_update_checked()
            if update_info is None:return bridge_ok({"has_update":False,"current_version":get_current_version()})
            return bridge_ok({"has_update":True,"current_version":get_current_version(),"new_version":update_info.version,"changelog":update_info.changelog,"release_url":update_info.release_url,"download_url":update_info.download_url,"file_size":update_info.file_size})
        except Exception as e:return bridge_error(str(e))
    def download_and_install_update(self,download_url:str,version:str)->dict:
        """Download and install an update."""
        try:
            if not is_bundled_app():return bridge_error("Updates only work when running as a bundled .app. For development, use git pull instead.")
            self._state.update_progress={"status":"downloading","percent":0}
            def on_progress(progress:DownloadProgress):self._state.update_progress={"status":"downloading","percent":progress.percent,"downloaded":progress.downloaded_bytes,"total":progress.total_bytes}
            update_info=UpdateInfo(version=version,download_url=download_url,changelog="",release_url="",file_size=0)
            dmg_path=asyncio.run(download_update(update_info,on_progress))
            if not dmg_path or not dmg_path.exists():self._state.update_progress={"status":"error","error":"Download failed"};return bridge_error("Failed to download update")
            self._state.update_progress={"status":"installing","percent":100}
            if not install_update(dmg_path):self._state.update_progress={"status":"error","error":"Install failed"};return bridge_error("Failed to start update installation")
            self._state.update_progress={"status":"restarting","percent":100}
            def quit_app():
                import time;time.sleep(1)
                if self._state.window:self._state.window.destroy()
                sys.exit(0)
            threading.Thread(target=quit_app,daemon=True).start()
            return bridge_ok({"message":"Update downloaded. Restarting to install..."})
        except Exception as e:self._state.update_progress={"status":"error","error":str(e)};return bridge_error(str(e))
    def get_update_progress(self)->dict:
        """Get the current update download/install progress."""
        p=self._state.update_progress
        if p is None:return bridge_ok({"status":"idle","percent":0})
        return bridge_ok(p)
    def skip_update_version(self,version:str)->dict:
        """Skip a specific version (don't prompt for this version again)."""
        try:save_update_settings(skipped_version=version);return bridge_ok()
        except Exception as e:return bridge_error(str(e))
    def get_update_settings(self)->dict:
        """Get update-related settings."""
        try:return bridge_ok(get_update_settings())
        except Exception as e:return bridge_error(str(e))
    def set_update_check_on_startup(self,enabled:bool)->dict:
        """Enable or disable automatic update checks on startup."""
        try:save_update_settings(check_on_startup=enabled);return bridge_ok()
        except Exception as e:return bridge_error(str(e))
