//GalleryModeToggle - Toggle between Assets and Ideas gallery modes
import{useGalleryMode}from'@/context/GalleryModeContext'
import{cn}from'@/lib/utils'
import{FolderOpen,Sparkles}from'lucide-react'
interface GalleryModeToggleProps{newCount:number}
export function GalleryModeToggle({newCount}:GalleryModeToggleProps){
const{contentMode,setContentMode}=useGalleryMode()
return(<div className="flex items-center gap-0.5 p-1 rounded-full bg-white/60 dark:bg-black/40 backdrop-blur-xl shadow-soft border border-black/5 dark:border-white/10">
<button onClick={()=>setContentMode('assets')} className={cn("relative flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-all","hover:bg-black/5 dark:hover:bg-white/10",contentMode==='assets'?"bg-white dark:bg-white/15 text-foreground shadow-sm":"text-muted-foreground")}>
<FolderOpen className="w-3.5 h-3.5"/>Assets
</button>
<button onClick={()=>setContentMode('ideas')} className={cn("relative flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-all","hover:bg-black/5 dark:hover:bg-white/10",contentMode==='ideas'?"bg-white dark:bg-white/15 text-foreground shadow-sm":"text-muted-foreground")}>
<Sparkles className="w-3.5 h-3.5"/>New Ideas
{newCount>0&&(<span className="absolute -top-1 -right-1 min-w-4 h-4 px-1 flex items-center justify-center rounded-full bg-brand-500 text-[10px] font-bold text-white">{newCount>9?'9+':newCount}</span>)}
</button>
</div>)
}
