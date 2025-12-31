import{useEffect}from'react'
import{ScrollArea}from'@/components/ui/scroll-area'
import{Button}from'@/components/ui/button'
import{Sparkles,AlertCircle,Loader2}from'lucide-react'
import{InspirationCard}from'./InspirationCard'
import{useInspirationContext}from'@/context/InspirationContext'
import{useProjects}from'@/context/ProjectContext'
interface InspirationsTabProps{brandSlug:string|null}
//Skeleton card for loading state
function SkeletonCard(){
return(
<div className="bg-white/50 dark:bg-white/5 rounded-xl p-4 space-y-3 animate-pulse">
<div className="h-4 bg-muted rounded w-3/4"/>
<div className="h-3 bg-muted rounded w-full"/>
<div className="h-3 bg-muted rounded w-2/3"/>
<div className="grid grid-cols-3 gap-2 pt-2">
<div className="aspect-square bg-muted rounded-lg"/>
<div className="aspect-square bg-muted rounded-lg"/>
<div className="aspect-square bg-muted rounded-lg"/>
</div>
</div>)
}
export function InspirationsTab({brandSlug}:InspirationsTabProps){
const{inspirations,isGenerating,error,triggerGeneration,save,dismiss,moreLikeThis,markViewed}=useInspirationContext()
const{projects,activeProject}=useProjects()
//Mark all visible inspirations as viewed when tab is displayed
useEffect(()=>{
if(!brandSlug)return
const readyIds=inspirations.filter(i=>i.status==='ready').map(i=>i.id)
readyIds.forEach(id=>markViewed(id))
},[inspirations,brandSlug,markViewed])
//No brand selected state
if(!brandSlug){
return(
<div className="flex-1 flex flex-col items-center justify-center px-6 py-12 text-center">
<div className="w-12 h-12 rounded-full bg-muted flex items-center justify-center mb-4">
<Sparkles className="w-6 h-6 text-muted-foreground"/>
</div>
<h3 className="text-sm font-medium text-foreground mb-1">Select a Brand</h3>
<p className="text-xs text-muted-foreground">Choose a brand to see creative inspirations</p>
</div>)
}
//Error state
if(error&&!isGenerating&&inspirations.length===0){
return(
<div className="flex-1 flex flex-col items-center justify-center px-6 py-12 text-center">
<div className="w-12 h-12 rounded-full bg-destructive/10 flex items-center justify-center mb-4">
<AlertCircle className="w-6 h-6 text-destructive"/>
</div>
<h3 className="text-sm font-medium text-foreground mb-1">Something went wrong</h3>
<p className="text-xs text-muted-foreground mb-4">{error}</p>
<Button variant="outline" size="sm" onClick={triggerGeneration}>Try Again</Button>
</div>)
}
//Empty state with generate button
if(inspirations.length===0&&!isGenerating){
return(
<div className="flex-1 flex flex-col items-center justify-center px-6 py-12 text-center">
<div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center mb-4">
<Sparkles className="w-6 h-6 text-primary"/>
</div>
<h3 className="text-sm font-medium text-foreground mb-1">No Inspirations Yet</h3>
<p className="text-xs text-muted-foreground mb-4">Generate creative ideas tailored to your brand</p>
<Button variant="default" size="sm" onClick={triggerGeneration}>
<Sparkles className="w-4 h-4 mr-1"/>Generate Ideas
</Button>
</div>)
}
//Loading state (no inspirations yet, generating)
if(inspirations.length===0&&isGenerating){
return(
<ScrollArea className="flex-1">
<div className="p-4 space-y-4">
<div className="flex items-center gap-2 text-sm text-muted-foreground mb-2">
<Loader2 className="w-4 h-4 animate-spin"/>
<span>Generating inspirations...</span>
</div>
<SkeletonCard/>
<SkeletonCard/>
<SkeletonCard/>
</div>
</ScrollArea>)
}
//Project list for save dropdown
const projectList=projects.map(p=>({slug:p.slug,name:p.name}))
//Filter to show only ready/generating inspirations (not saved/dismissed)
const visibleInspirations=inspirations.filter(i=>i.status==='ready'||i.status==='generating')
return(
<ScrollArea className="flex-1">
<div className="p-4 space-y-4">
{/* Generating indicator */}
{isGenerating&&(
<div className="flex items-center gap-2 text-sm text-muted-foreground mb-2">
<Loader2 className="w-4 h-4 animate-spin"/>
<span>Generating new inspirations...</span>
</div>
)}
{/* Inspiration cards */}
{visibleInspirations.map(insp=>(
<InspirationCard key={insp.id} inspiration={insp} activeProject={activeProject} projects={projectList} onSaveImage={save} onMoreLikeThis={moreLikeThis} onDismiss={dismiss}/>
))}
{/* Generate more button */}
{!isGenerating&&visibleInspirations.length>0&&(
<Button variant="outline" size="sm" className="w-full" onClick={triggerGeneration}>
<Sparkles className="w-4 h-4 mr-1"/>Generate More Ideas
</Button>
)}
</div>
</ScrollArea>)
}
