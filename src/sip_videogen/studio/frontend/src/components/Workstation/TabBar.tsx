//Tab bar component with horizontal scrollable tabs and context menu
import{useRef}from'react'
import{useTabs}from'@/context/TabContext'
import{TabButton}from'./TabButton'
import{ContextMenu,ContextMenuTrigger,ContextMenuContent,ContextMenuItem,ContextMenuSeparator}from'@/components/ui/context-menu'
import{ScrollArea,ScrollBar}from'@/components/ui/scroll-area'
export function TabBar(){
const{tabs,activeTabId,setActiveTab,requestCloseTab,requestCloseAllTabs,requestCloseOtherTabs}=useTabs()
const ctxTabIdRef=useRef<string|null>(null)
if(tabs.length===0)return null
return(<div className="flex-shrink-0 border-b bg-muted/20">
<ScrollArea className="w-full whitespace-nowrap"><div className="flex">
{tabs.map(tab=>(
<ContextMenu key={tab.id} onOpenChange={open=>{if(open)ctxTabIdRef.current=tab.id}}>
<ContextMenuTrigger asChild>
<div><TabButton tab={tab} isActive={tab.id===activeTabId} onClick={()=>setActiveTab(tab.id)} onClose={e=>{e.stopPropagation();requestCloseTab(tab.id)}}/></div>
</ContextMenuTrigger>
<ContextMenuContent>
<ContextMenuItem onClick={()=>ctxTabIdRef.current&&requestCloseTab(ctxTabIdRef.current)}>Close</ContextMenuItem>
<ContextMenuItem onClick={()=>ctxTabIdRef.current&&requestCloseOtherTabs(ctxTabIdRef.current)}>Close Others</ContextMenuItem>
<ContextMenuSeparator/>
<ContextMenuItem onClick={requestCloseAllTabs}>Close All</ContextMenuItem>
</ContextMenuContent>
</ContextMenu>))}
</div><ScrollBar orientation="horizontal"/></ScrollArea>
</div>)}
