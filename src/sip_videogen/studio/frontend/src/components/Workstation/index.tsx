//Workstation component - tab container for IDE-like tabbed interface
import{useRef,useEffect,useCallback}from'react'
import{useTabs}from'@/context/TabContext'
import{useBrand}from'@/context/BrandContext'
import{TabBar}from'./TabBar'
import{ProjectTabContent}from'./ProjectTabContent'
import{ProductTabContent}from'./ProductTabContent'
import{TemplateTabContent}from'./TemplateTabContent'
import{EmptyState}from'./EmptyState'
import{cn}from'@/lib/utils'
//Tab content wrapper - renders content based on tab type
function TabContent({type,slug,isActive}:{type:string;slug:string;isActive:boolean}){
//Use display:none for hidden tabs (keeps them mounted, preserves state)
return(<div className={cn("flex-1 flex flex-col min-h-0",isActive?"":"hidden")} style={{display:isActive?'flex':'none'}}>
{type==='project'&&<ProjectTabContent projectSlug={slug} isActive={isActive}/>}
{type==='product'&&<ProductTabContent productSlug={slug} isActive={isActive}/>}
{type==='template'&&<TemplateTabContent templateSlug={slug} isActive={isActive}/>}
</div>)}
//Check if target is an interactive element that should capture keyboard input
function isInteractiveElement(el:EventTarget|null):boolean{if(!el||!(el instanceof HTMLElement))return false
const tag=el.tagName.toLowerCase()
if(tag==='input'||tag==='textarea'||tag==='select')return true
if(el.isContentEditable)return true
return false}
export function Workstation(){
const containerRef=useRef<HTMLDivElement>(null)
const{tabs,activeTabId,requestCloseTab}=useTabs()
const{activeBrand}=useBrand()
const hasTabs=tabs.length>0
//Cmd+W / Ctrl+W keyboard shortcut to close active tab
const handleKeyDown=useCallback((e:KeyboardEvent)=>{
//Only handle Cmd+W (Mac) or Ctrl+W (Windows/Linux)
const isMac=navigator.platform.toUpperCase().indexOf('MAC')>=0
const modKey=isMac?e.metaKey:e.ctrlKey
if(!modKey||e.key.toLowerCase()!=='w')return
//Skip if focus is in interactive element (input, textarea, contenteditable)
if(isInteractiveElement(e.target))return
//Skip if focus is not within workstation container (use composedPath for shadow DOM)
if(containerRef.current&&!e.composedPath().includes(containerRef.current))return
//Prevent browser from closing tab
e.preventDefault()
e.stopPropagation()
//Close active tab if exists
if(activeTabId)requestCloseTab(activeTabId)},[activeTabId,requestCloseTab])
useEffect(()=>{document.addEventListener('keydown',handleKeyDown,true)
return()=>document.removeEventListener('keydown',handleKeyDown,true)},[handleKeyDown])
//No brand selected - show empty state
if(!activeBrand)return(<div className="flex-1 flex flex-col min-w-0 overflow-hidden bg-gradient-to-br from-gray-50 to-gray-200 dark:from-gray-900 dark:to-black"><EmptyState/></div>)
return(<div ref={containerRef} tabIndex={-1} className="flex-1 flex flex-col min-w-0 overflow-hidden bg-gradient-to-br from-gray-50 to-gray-200 dark:from-gray-900 dark:to-black outline-none">
{/* Tab Bar - always visible when brand selected */}
<TabBar/>
{/* Tab Content Area */}
{hasTabs?(
//Render all tabs (hidden via CSS when not active)
tabs.map(tab=>(<TabContent key={tab.id} type={tab.type} slug={tab.slug} isActive={tab.id===activeTabId}/>))
):(<EmptyState/>)}
</div>)}
