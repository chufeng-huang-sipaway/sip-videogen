import{useState,useEffect,useCallback}from'react'
import{Brain,RefreshCw,History,AlertCircle,CheckCircle,FolderOpen,MoreHorizontal,Sparkles,Palette,MessageSquare,Users,Target,ShieldAlert}from'lucide-react'
import{Button}from'@/components/ui/button'
import{Dialog,DialogContent,DialogDescription,DialogHeader,DialogTitle}from'@/components/ui/dialog'
import{ScrollArea}from'@/components/ui/scroll-area'
import{Alert,AlertDescription}from'@/components/ui/alert'
import{Spinner}from'@/components/ui/spinner'
import{Tabs,TabsContent,TabsList,TabsTrigger}from'@/components/ui/tabs'
import{DropdownMenu,DropdownMenuContent,DropdownMenuItem,DropdownMenuTrigger}from'@/components/ui/dropdown-menu'
import{useBrand}from'@/context/BrandContext'
import{bridge,isPyWebView}from'@/lib/bridge'
import{cn}from'@/lib/utils'
import{CoreSection}from'./sections/CoreSection'
import{VisualSection}from'./sections/VisualSection'
import{VoiceSection}from'./sections/VoiceSection'
import{AudienceSection}from'./sections/AudienceSection'
import{PositioningSection}from'./sections/PositioningSection'
import{ConstraintsAvoidSection}from'./sections/ConstraintsAvoidSection'
import{RegenerateConfirmDialog}from'./RegenerateConfirmDialog'
import{BackupDialog}from'./BackupDialog'
import{FilesTab}from'./FilesTab'
import{toast}from'@/components/ui/toaster'
//Section definitions for vertical tabs navigation
const MEMORY_SECTIONS=[{id:'core',label:'Core Identity',icon:Sparkles},{id:'visual',label:'Visual Style',icon:Palette},{id:'voice',label:'Voice & Tone',icon:MessageSquare},{id:'audience',label:'Audience',icon:Users},{id:'positioning',label:'Positioning',icon:Target},{id:'constraints',label:'Constraints',icon:ShieldAlert}]as const
type MemorySectionId=(typeof MEMORY_SECTIONS)[number]['id']
interface BrandMemoryProps{open:boolean;onOpenChange:(open:boolean)=>void}
export function BrandMemory({open,onOpenChange}:BrandMemoryProps){
//Use context for identity state (single source of truth)
const{activeBrand,identity,isIdentityLoading:isLoading,identityError:error,refreshIdentity,setIdentity,refresh:refreshBrands}=useBrand()
//Local state for regeneration and backup (component-specific)
const[showRegenerateConfirm,setShowRegenerateConfirm]=useState(false)
const[isRegenerating,setIsRegenerating]=useState(false)
const[regenerateError,setRegenerateError]=useState<string|null>(null)
const[regenerateSuccess,setRegenerateSuccess]=useState(false)
const[showBackupDialog,setShowBackupDialog]=useState(false)
const[activeSection,setActiveSection]=useState<MemorySectionId>('core')
//Load identity when dialog opens
useEffect(()=>{if(open&&activeBrand){refreshIdentity()}},[open,activeBrand,refreshIdentity])
//Reset regenerate state when dialog closes
useEffect(()=>{if(!open){setRegenerateError(null);setRegenerateSuccess(false)}},[open])
//Format last updated date
const formatLastUpdated=(isoString:string):{relative:string;absolute:string}=>{
const date=new Date(isoString);const now=new Date();const diffMs=now.getTime()-date.getTime();const diffDays=Math.round(diffMs/(1000*60*60*24))
const absolute=date.toLocaleString(undefined,{weekday:'short',year:'numeric',month:'short',day:'numeric',hour:'2-digit',minute:'2-digit'})
if(diffDays<0)return{relative:'Updated recently',absolute}
if(diffDays===0)return{relative:'Updated today',absolute}
if(diffDays===1)return{relative:'Updated yesterday',absolute}
if(diffDays<7)return{relative:`Updated ${diffDays} days ago`,absolute}
return{relative:`Updated ${date.toLocaleDateString()}`,absolute}}
const handleClose=()=>onOpenChange(false)
//Handle regenerate confirmation
const handleRegenerateConfirm=useCallback(async()=>{
if(!isPyWebView())return
setIsRegenerating(true);setRegenerateError(null);setRegenerateSuccess(false);setShowRegenerateConfirm(false)
try{const newIdentity=await bridge.regenerateBrandIdentity(true)
setIdentity(newIdentity);await refreshBrands();setRegenerateSuccess(true);toast.success('Brand identity regenerated successfully')
setTimeout(()=>setRegenerateSuccess(false),5000)
}catch(err){setRegenerateError(err instanceof Error?err.message:'Failed to regenerate brand identity')
}finally{setIsRegenerating(false)}},[setIdentity,refreshBrands])
//Handle backup restore
const handleBackupRestore=useCallback((restoredIdentity:typeof identity)=>{
if(restoredIdentity){setIdentity(restoredIdentity);toast.success('Brand identity restored from backup')}},[setIdentity])
return(<Dialog open={open} onOpenChange={handleClose}>
<DialogContent className="max-w-3xl h-[85vh] flex flex-col overflow-hidden">
<DialogHeader className="flex-shrink-0 pb-0">
<DialogTitle className="flex items-center gap-2"><Brain className="h-5 w-5 text-purple-500"/>Brand Memory</DialogTitle>
<DialogDescription className="flex items-center gap-2">
{identity?`What the AI knows about ${identity.core.name}`:'Loading brand identity...'}
{identity&&(<><span className="text-muted-foreground/50">·</span><span className="cursor-help" title={formatLastUpdated(identity.updated_at).absolute}>{formatLastUpdated(identity.updated_at).relative}</span></>)}
</DialogDescription>
</DialogHeader>
{/* Tabs content area */}
<Tabs defaultValue="memory" className="flex-1 flex flex-col min-h-0">
<div className="flex items-center justify-between flex-shrink-0 border-b border-border">
<TabsList className="h-10 bg-transparent p-0 border-0">
<TabsTrigger value="memory" className="gap-1.5 rounded-none border-b-2 border-transparent data-[state=active]:border-purple-500 data-[state=active]:bg-transparent data-[state=active]:shadow-none focus-visible:outline-none focus-visible:ring-0"><Brain className="h-4 w-4"/>Memory</TabsTrigger>
<TabsTrigger value="files" className="gap-1.5 rounded-none border-b-2 border-transparent data-[state=active]:border-purple-500 data-[state=active]:bg-transparent data-[state=active]:shadow-none focus-visible:outline-none focus-visible:ring-0"><FolderOpen className="h-4 w-4"/>Files</TabsTrigger>
</TabsList>
{identity&&!isLoading&&(<DropdownMenu><DropdownMenuTrigger asChild>
<Button variant="ghost" size="sm" className="h-8 w-8 p-0" disabled={isRegenerating}>{isRegenerating?<Spinner className="h-4 w-4"/>:<MoreHorizontal className="h-4 w-4"/>}<span className="sr-only">Actions</span></Button>
</DropdownMenuTrigger>
<DropdownMenuContent align="end">
<DropdownMenuItem onClick={()=>setShowRegenerateConfirm(true)} disabled={isRegenerating}><RefreshCw className="h-4 w-4 mr-2"/>Regenerate from files</DropdownMenuItem>
<DropdownMenuItem onClick={()=>setShowBackupDialog(true)} disabled={isRegenerating}><History className="h-4 w-4 mr-2"/>View history</DropdownMenuItem>
</DropdownMenuContent>
</DropdownMenu>)}
</div>
{/* Memory Tab */}
<TabsContent value="memory" className="flex-1 min-h-0 mt-0">
{isRegenerating&&(<div className="h-full flex items-center justify-center"><div className="flex flex-col items-center gap-4"><Spinner className="h-8 w-8 text-purple-500"/><p className="text-sm text-muted-foreground">Regenerating brand identity from source materials...</p><p className="text-xs text-muted-foreground">A backup has been created automatically</p></div></div>)}
{isLoading&&!isRegenerating&&(<div className="h-full flex items-center justify-center"><div className="flex flex-col items-center gap-4"><Spinner className="h-8 w-8 text-purple-500"/><p className="text-sm text-muted-foreground">Loading brand memory...</p></div></div>)}
{error&&!isLoading&&!isRegenerating&&(<div className="p-4"><Alert variant="destructive"><AlertCircle className="h-4 w-4"/><AlertDescription>{error}</AlertDescription></Alert></div>)}
{!activeBrand&&!isLoading&&!isRegenerating&&(<div className="h-full flex items-center justify-center"><p className="text-sm text-muted-foreground">No brand selected. Please select a brand from the sidebar.</p></div>)}
{identity&&!isLoading&&!error&&!isRegenerating&&(<div className="h-full flex gap-0">
<nav className="w-44 flex-shrink-0 border-r border-border pr-2 py-2"><ul className="space-y-1">
{MEMORY_SECTIONS.map((section)=>{const Icon=section.icon;const isActive=activeSection===section.id
return(<li key={section.id}><button onClick={()=>setActiveSection(section.id)} className={cn('w-full flex items-center gap-2.5 px-3 py-2 rounded-md text-sm font-medium transition-colors','hover:bg-muted/50',isActive?'bg-purple-100 text-purple-900 dark:bg-purple-900/30 dark:text-purple-100':'text-muted-foreground hover:text-foreground')}><Icon className={cn('h-4 w-4',isActive&&'text-purple-600 dark:text-purple-400')}/>{section.label}</button></li>)})}
</ul></nav>
<div className="flex-1 min-w-0 min-h-0 pl-4 flex flex-col">
{regenerateSuccess&&(<Alert className="mb-4 flex-shrink-0 bg-green-50 text-green-800 border-green-200 dark:bg-green-900/20 dark:text-green-400 dark:border-green-800"><CheckCircle className="h-4 w-4 text-green-600 dark:text-green-400"/><AlertDescription>Brand identity regenerated successfully. AI context refreshed automatically.</AlertDescription></Alert>)}
{regenerateError&&(<Alert variant="destructive" className="mb-4 flex-shrink-0"><AlertCircle className="h-4 w-4"/><AlertDescription>{regenerateError}</AlertDescription></Alert>)}
<ScrollArea className="flex-1 min-h-0"><div className="pr-4 pb-4">
{activeSection==='core'&&<CoreSection data={identity.core}/>}
{activeSection==='visual'&&<VisualSection data={identity.visual}/>}
{activeSection==='voice'&&<VoiceSection data={identity.voice}/>}
{activeSection==='audience'&&<AudienceSection data={identity.audience}/>}
{activeSection==='positioning'&&<PositioningSection data={identity.positioning}/>}
{activeSection==='constraints'&&<ConstraintsAvoidSection data={{constraints:identity.constraints,avoid:identity.avoid}}/>}
</div></ScrollArea>
</div>
</div>)}
</TabsContent>
{/* Files Tab */}
<TabsContent value="files" className="flex-1 min-h-0 mt-0">
{activeBrand?<FilesTab/>:(<div className="h-full flex items-center justify-center"><p className="text-sm text-muted-foreground">No brand selected. Please select a brand from the sidebar.</p></div>)}
</TabsContent>
</Tabs>
</DialogContent>
<RegenerateConfirmDialog open={showRegenerateConfirm} onOpenChange={setShowRegenerateConfirm} onConfirm={handleRegenerateConfirm} brandName={identity?.core.name??'this brand'}/>
<BackupDialog open={showBackupDialog} onOpenChange={setShowBackupDialog} brandName={identity?.core.name??'this brand'} onRestore={handleBackupRestore}/>
</Dialog>)}
