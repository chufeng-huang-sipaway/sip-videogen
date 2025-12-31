import{ChatPanelContent}from'@/components/ChatPanel'
import{useBrand}from'@/context/BrandContext'
//RightSidebar now shows only Chat (Inspirations moved to center gallery)
export function RightSidebar(){
const{activeBrand}=useBrand()
const brandSlug=activeBrand
return(
<div className="w-[320px] flex-shrink-0 flex flex-col h-screen glass-sidebar border-l border-white/10">
{/* Chat header */}
<div className="px-4 pt-4 pb-2">
<div className="flex items-center justify-center h-9 bg-white/50 dark:bg-white/10 rounded-lg">
<span className="text-xs font-medium text-neutral-600 dark:text-neutral-300">Chat</span>
</div>
</div>
{/* Chat content */}
<div className="flex-1 flex flex-col min-h-0">
<ChatPanelContent brandSlug={brandSlug}/>
</div>
</div>
)
}
