//Tab button component for tab bar (VS Code-like styling)
import{FolderOpen,Package,Layout,X}from'lucide-react'
import{cn}from'@/lib/utils'
import type{Tab}from'@/types/tabs'
const typeIcons={project:FolderOpen,product:Package,template:Layout}
interface TabButtonProps{tab:Tab;isActive:boolean;onClick:()=>void;onClose:(e:React.MouseEvent)=>void}
export function TabButton({tab,isActive,onClick,onClose}:TabButtonProps){
const Icon=typeIcons[tab.type]
return(<button onClick={onClick} className={cn("group relative flex items-center gap-2 px-3 py-1.5 text-sm border-b-2 transition-colors","hover:bg-muted/50 min-w-0 max-w-[200px]",isActive?"border-primary bg-muted/30 text-foreground":"border-transparent text-muted-foreground hover:text-foreground")}>
<Icon className="w-4 h-4 flex-shrink-0"/>
<span className="truncate">{tab.title}</span>
{tab.isDirty&&<span className="ml-0.5 text-blue-500 flex-shrink-0">•</span>}
<span onClick={onClose} className={cn("ml-1 p-0.5 rounded hover:bg-muted-foreground/20 flex-shrink-0 transition-opacity",isActive||tab.isDirty?"opacity-100":"opacity-0 group-hover:opacity-100")}><X className="w-3.5 h-3.5"/></span>
</button>)}
