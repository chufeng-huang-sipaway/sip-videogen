import{useEffect,useState}from'react'
import{Plus,Check,Trash2,Building2,ChevronsUpDown,Loader2,X}from'lucide-react'
import{Button}from'@/components/ui/button'
import{Tooltip,TooltipContent,TooltipTrigger}from'@/components/ui/tooltip'
import{DropdownMenu,DropdownMenuContent,DropdownMenuItem,DropdownMenuSeparator,DropdownMenuTrigger}from'@/components/ui/dropdown-menu'
import{useBrand}from'@/context/BrandContext'
import{DeleteBrandDialog}from'@/components/Brand/DeleteBrandDialog'
import{CreateBrandDialog}from'@/components/Brand/CreateBrandDialog'
import{cn}from'@/lib/utils'
import{bridge}from'@/lib/bridge'
const CONTENT_DURATION=150
const WIDTH_DURATION=250
const EASING='cubic-bezier(0.4, 0, 0.2, 1)'
//Human-readable phase labels
const phaseLabels:Record<string,string>={starting:'Starting...',researching:'Researching...',creating:'Creating identity...',finalizing:'Finalizing...',complete:'Complete',failed:'Failed'}
interface BrandSelectorProps{compact?:boolean;showContent?:boolean;allowTooltips?:boolean;onDropdownOpenChange?:(open:boolean)=>void}
export function BrandSelector({compact,showContent=true,allowTooltips=true,onDropdownOpenChange}:BrandSelectorProps){
const{brands,activeBrand,isLoading,selectBrand,refresh,creatingBrand,clearBrandCreationJob}=useBrand()
const[deleteDialogOpen,setDeleteDialogOpen]=useState(false)
const[createDialogOpen,setCreateDialogOpen]=useState(false)
const[dropdownOpen,setDropdownOpen]=useState(false)
const handleDropdownChange=(open:boolean)=>{setDropdownOpen(open);onDropdownOpenChange?.(open)}
//Delay the compact morph on collapse so the label can fade out first (prevents text/avatar overlap).
const[visualCompact,setVisualCompact]=useState(Boolean(compact))
const[isTransitioning,setIsTransitioning]=useState(false)
const currentBrand=brands.find(b=>b.slug===activeBrand)
const getInitials=(name:string)=>{const words=name.split(/\s+/);if(words.length>=2)return(words[0][0]+words[1][0]).toUpperCase();return name.slice(0,2).toUpperCase()}
const contentTransition=`opacity ${CONTENT_DURATION}ms ${EASING}, visibility ${CONTENT_DURATION}ms ${EASING}, transform ${CONTENT_DURATION}ms ${EASING}`
const sizeTransition=`width ${WIDTH_DURATION}ms ${EASING}, height ${WIDTH_DURATION}ms ${EASING}, padding ${WIDTH_DURATION}ms ${EASING}`
//Check if there's an active job (running or pending)
const hasActiveJob=creatingBrand&&(creatingBrand.status==='running'||creatingBrand.status==='pending')
const hasFailedJob=creatingBrand&&(creatingBrand.status==='failed'||creatingBrand.status==='cancelled')
useEffect(()=>{
const shouldBeCompact=Boolean(compact)
setIsTransitioning(true)
const endTransition=setTimeout(()=>setIsTransitioning(false),WIDTH_DURATION)
if(!shouldBeCompact){setVisualCompact(false);return()=>clearTimeout(endTransition)}
const t=setTimeout(()=>setVisualCompact(true),CONTENT_DURATION)
return()=>{clearTimeout(t);clearTimeout(endTransition)}},[compact])
if(isLoading){return(<Button variant="ghost" className={cn("rounded-xl bg-primary/10",visualCompact?"w-12 h-12 p-0":"w-full h-auto py-3 px-3")} style={{transition:sizeTransition}} disabled><Building2 className="w-5 h-5 animate-pulse"/></Button>)}
//Handle cancel job
const handleCancelJob=async(e:React.MouseEvent)=>{e.stopPropagation();try{await bridge.cancelBrandCreation()}catch(err){console.warn('[BrandSelector] Failed to cancel job:',err)}}
//Handle clear failed job
const handleClearJob=async(e:React.MouseEvent)=>{e.stopPropagation();await clearBrandCreationJob()}
const dropdownContent=(
<DropdownMenuContent className="w-60" side={compact?"right":"bottom"} align={compact?"start":"center"} sideOffset={4}>
{/* Creating brand placeholder */}
{hasActiveJob&&creatingBrand&&(<>
<DropdownMenuItem disabled className="py-2.5 opacity-100">
<div className="flex items-center gap-2 flex-1">
<Loader2 className="h-4 w-4 animate-spin text-brand-500"/>
<div className="flex-1 min-w-0">
<div className="font-medium truncate">{creatingBrand.brand_name}</div>
<div className="text-xs text-muted-foreground">{phaseLabels[creatingBrand.phase]||creatingBrand.phase}</div>
</div>
</div>
<button onClick={handleCancelJob} className="p-1 hover:bg-muted rounded" title="Cancel"><X className="h-3 w-3 text-muted-foreground"/></button>
</DropdownMenuItem>
<DropdownMenuSeparator/>
</>)}
{/* Failed job entry */}
{hasFailedJob&&creatingBrand&&(<>
<DropdownMenuItem disabled className="py-2.5 opacity-100">
<div className="flex items-center gap-2 flex-1">
<div className="h-4 w-4 rounded-full bg-destructive/20 flex items-center justify-center"><X className="h-3 w-3 text-destructive"/></div>
<div className="flex-1 min-w-0">
<div className="font-medium truncate">{creatingBrand.brand_name}</div>
<div className="text-xs text-destructive truncate">{creatingBrand.status==='cancelled'?'Cancelled':creatingBrand.error||'Failed'}</div>
</div>
</div>
<button onClick={handleClearJob} className="p-1 hover:bg-muted rounded" title="Dismiss"><X className="h-3 w-3 text-muted-foreground"/></button>
</DropdownMenuItem>
<DropdownMenuSeparator/>
</>)}
{brands.length===0&&!hasActiveJob&&!hasFailedJob?(
<DropdownMenuItem disabled>No brands found</DropdownMenuItem>
):(
brands.map((brand)=>(<DropdownMenuItem key={brand.slug} onClick={()=>selectBrand(brand.slug)} className="py-2.5">
<span className="flex-1 font-medium">{brand.name}</span>
{brand.slug===activeBrand&&<Check className="h-4 w-4 text-primary"/>}
</DropdownMenuItem>))
)}
<DropdownMenuSeparator/>
<DropdownMenuItem onClick={()=>setCreateDialogOpen(true)} className="py-2.5 text-muted-foreground focus:text-foreground" disabled={!!hasActiveJob}>
<Plus className="h-4 w-4 mr-2"/>
Create New Brand
</DropdownMenuItem>
{currentBrand&&(<>
<DropdownMenuSeparator/>
<DropdownMenuItem className="text-destructive focus:text-destructive py-2.5" onClick={()=>setDeleteDialogOpen(true)}>
<Trash2 className="h-4 w-4 mr-2"/>
Delete "{currentBrand.name}"
</DropdownMenuItem>
</>)}
</DropdownMenuContent>
)
const dialogs=(<>
<DeleteBrandDialog brand={currentBrand??null} open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen} onDeleted={refresh}/>
<CreateBrandDialog open={createDialogOpen} onOpenChange={setCreateDialogOpen} onCreated={async(slug)=>{await refresh();await selectBrand(slug)}} hasActiveJob={hasActiveJob||false}/>
</>)
//Unified structure - same DOM, CSS handles compact/expanded with sequenced timing
const showLabels=showContent&&!visualCompact
return(
<DropdownMenu open={dropdownOpen} onOpenChange={handleDropdownChange}>
<Tooltip open={visualCompact&&allowTooltips&&!dropdownOpen?undefined:false}>
<TooltipTrigger asChild>
<DropdownMenuTrigger asChild>
<Button variant="ghost" className={cn("justify-start rounded-2xl bg-gradient-to-br from-white to-neutral-50 dark:from-neutral-900 dark:to-neutral-950 border border-white/20 overflow-hidden",!isTransitioning&&"shadow-sm hover:shadow-md",visualCompact?"w-12 h-12 p-0":"w-full h-auto py-3.5 px-3")} style={{transition:`${sizeTransition}, box-shadow 150ms ease`}}>
<div className="flex items-center gap-3 text-left">
<div className={cn("rounded-xl bg-brand-500/10 text-brand-600 flex items-center justify-center font-bold shrink-0",!isTransitioning&&"shadow-inner",visualCompact?"w-12 h-12 text-base":"w-10 h-10 text-sm")} style={{transition:sizeTransition}}>{currentBrand?getInitials(currentBrand.name):<Building2 className="w-5 h-5"/>}</div>
{!visualCompact&&(
<div className="flex-1 min-w-0" style={{transition:contentTransition,opacity:showLabels?1:0,visibility:showLabels?'visible':'hidden',transform:'translateX(0)'}}>
<div className="font-semibold text-sm truncate leading-none mb-1">{currentBrand?.name||'Select Brand'}</div>
<div className="text-[10px] text-muted-foreground/70 font-medium">{hasActiveJob?'Creating...':'Brand Workspace'}</div>
</div>
)}
</div>
{!visualCompact&&(
<ChevronsUpDown className="h-4 w-4 text-muted-foreground/40" style={{transition:contentTransition,opacity:showLabels?1:0,visibility:showLabels?'visible':'hidden',transform:'translateX(0)'}}/>
)}
</Button>
</DropdownMenuTrigger>
</TooltipTrigger>
{compact&&<TooltipContent side="right" className="font-semibold">{currentBrand?.name||'Select Brand'}</TooltipContent>}
</Tooltip>
{dropdownContent}
{dialogs}
</DropdownMenu>
)}
