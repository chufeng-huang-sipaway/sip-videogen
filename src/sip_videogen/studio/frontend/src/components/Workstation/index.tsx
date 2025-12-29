//Workstation component - tab container for IDE-like tabbed interface
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
export function Workstation(){
const{tabs,activeTabId}=useTabs()
const{activeBrand}=useBrand()
const hasTabs=tabs.length>0
//No brand selected - show empty state
if(!activeBrand)return(<div className="flex-1 flex flex-col min-w-0 overflow-hidden bg-gradient-to-br from-gray-50 to-gray-200 dark:from-gray-900 dark:to-black"><EmptyState/></div>)
return(<div className="flex-1 flex flex-col min-w-0 overflow-hidden bg-gradient-to-br from-gray-50 to-gray-200 dark:from-gray-900 dark:to-black">
{/* Tab Bar - always visible when brand selected */}
<TabBar/>
{/* Tab Content Area */}
{hasTabs?(
//Render all tabs (hidden via CSS when not active)
tabs.map(tab=>(<TabContent key={tab.id} type={tab.type} slug={tab.slug} isActive={tab.id===activeTabId}/>))
):(<EmptyState/>)}
</div>)}
