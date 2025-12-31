import{useState,useEffect}from'react'
import{Tabs,TabsList,TabsTrigger}from'@/components/ui/tabs'
import{ChatPanelContent}from'@/components/ChatPanel'
import{InspirationsTab}from'./InspirationsTab'
import{TabIndicator}from'./TabIndicator'
import{InspirationProvider,useInspirationContext}from'@/context/InspirationContext'
import{cn}from'@/lib/utils'
const TAB_STORAGE_KEY='sip-studio-active-tab'
type RightSidebarTab='inspirations'|'chat'
interface RightSidebarProps{brandSlug:string|null}
//Inner component that uses InspirationContext
function RightSidebarContent({brandSlug}:RightSidebarProps){
const[activeTab,setActiveTab]=useState<RightSidebarTab>(()=>{
const stored=localStorage.getItem(TAB_STORAGE_KEY)
return(stored==='chat'||stored==='inspirations')?stored:'inspirations'
})
const{isGenerating,newCount}=useInspirationContext()
useEffect(()=>{localStorage.setItem(TAB_STORAGE_KEY,activeTab)},[activeTab])
return(
<div className="w-[320px] flex-shrink-0 flex flex-col h-screen glass-sidebar border-l border-white/10">
{/* Tab header */}
<div className="px-4 pt-4 pb-2">
<Tabs value={activeTab} onValueChange={(v)=>setActiveTab(v as RightSidebarTab)} className="w-full">
<TabsList className="w-full bg-white/50 dark:bg-white/10 p-0.5 h-9">
<TabsTrigger value="inspirations" className="flex-1 gap-1.5 data-[state=active]:bg-white dark:data-[state=active]:bg-white/20 data-[state=active]:shadow-sm rounded-md text-xs font-medium h-8">
Inspirations
<TabIndicator isGenerating={isGenerating} newCount={newCount}/>
</TabsTrigger>
<TabsTrigger value="chat" className="flex-1 data-[state=active]:bg-white dark:data-[state=active]:bg-white/20 data-[state=active]:shadow-sm rounded-md text-xs font-medium h-8">
Chat
</TabsTrigger>
</TabsList>
</Tabs>
</div>
{/* Tab content - forceMount preserves state, hidden class hides visually */}
<div className="flex-1 flex flex-col min-h-0">
<div className={cn("flex-1 flex flex-col min-h-0",activeTab!=='inspirations'&&'hidden')}>
<InspirationsTab brandSlug={brandSlug}/>
</div>
<div className={cn("flex-1 flex flex-col min-h-0",activeTab!=='chat'&&'hidden')}>
<ChatPanelContent brandSlug={brandSlug}/>
</div>
</div>
</div>
)
}
export function RightSidebar({brandSlug}:RightSidebarProps){
return(
<InspirationProvider brandSlug={brandSlug}>
<RightSidebarContent brandSlug={brandSlug}/>
</InspirationProvider>
)
}
