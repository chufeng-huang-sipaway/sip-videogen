//TemplateTabContent - inline editing view for template tabs
import{useCallback,useRef,useEffect,useState,useMemo}from'react'
import{Layout,X,Star,Loader2,Trash2,Plus,Save,AlertTriangle,RefreshCw,ChevronDown,ChevronRight}from'lucide-react'
import{Button}from'@/components/ui/button'
import{Input}from'@/components/ui/input'
import{Dropzone,DropzoneEmptyState}from'@/components/ui/dropzone'
import{AlertDialog,AlertDialogAction,AlertDialogCancel,AlertDialogContent,AlertDialogDescription,AlertDialogFooter,AlertDialogHeader,AlertDialogTitle}from'@/components/ui/alert-dialog'
import{useTemplates}from'@/context/TemplateContext'
import{useTabs}from'@/context/TabContext'
import{useBrand}from'@/context/BrandContext'
import{makeTabId}from'@/types/tabs'
import{processImageFiles}from'@/lib/file-utils'
import type{ProcessedFile}from'@/lib/file-utils'
import{bridge,isPyWebView,isV2Analysis}from'@/lib/bridge'
import{getAllowedImageExts}from'@/lib/constants'
import{toast}from'@/components/ui/toaster'
import type{TemplateFull,TemplateAnalysis}from'@/lib/bridge'
import{cn}from'@/lib/utils'
interface Props{templateSlug:string;isActive:boolean}
type LoadState='loading'|'loaded'|'error'|'not-found'
interface ExistingImage{path:string;filename:string;thumbnailUrl:string|null;isPrimary:boolean}
export function TemplateTabContent({templateSlug,isActive}:Props){
const{activeBrand}=useBrand()
const{getTemplate,getTemplateImages,updateTemplate,uploadTemplateImage,deleteTemplateImage,setPrimaryTemplateImage,deleteTemplate,reanalyzeTemplate,refresh}=useTemplates()
const{setTabDirty,updateTabTitle,closeTab}=useTabs()
//Compute tab ID from brand + type + slug
const tabId=useMemo(()=>activeBrand?makeTabId(activeBrand,'template',templateSlug):'',[activeBrand,templateSlug])
const[loadState,setLoadState]=useState<LoadState>('loading')
const[error,setError]=useState<string|null>(null)
const[originalTemplate,setOriginalTemplate]=useState<TemplateFull|null>(null)
//Editable fields
const[name,setName]=useState('')
const[description,setDescription]=useState('')
const[defaultStrict,setDefaultStrict]=useState(true)
//Image management
const[existingImages,setExistingImages]=useState<ExistingImage[]>([])
const[newImages,setNewImages]=useState<ProcessedFile[]>([])
const[imagesToDelete,setImagesToDelete]=useState<string[]>([])
const[uploadError,setUploadError]=useState<string|null>(null)
//Saving/Deleting/Reanalyzing state
const[isSaving,setIsSaving]=useState(false)
const[showDeleteConfirm,setShowDeleteConfirm]=useState(false)
const[isDeleting,setIsDeleting]=useState(false)
const[isReanalyzing,setIsReanalyzing]=useState(false)
//Analysis section collapse state
const[analysisOpen,setAnalysisOpen]=useState(true)
//Race condition handling
const requestIdRef=useRef(0)
//Compute dirty state
const isDirty=originalTemplate!==null&&(name.trim()!==originalTemplate.name||description.trim()!==originalTemplate.description||defaultStrict!==originalTemplate.default_strict||newImages.length>0||imagesToDelete.length>0||existingImages.some(img=>img.isPrimary&&img.path!==originalTemplate.primary_image))
//Update dirty state in TabContext
useEffect(()=>{if(!isActive||!tabId)return
setTabDirty(tabId,isDirty)},[isActive,tabId,isDirty,setTabDirty])
//Load template data
useEffect(()=>{if(!isActive)return
const thisRequestId=++requestIdRef.current
setLoadState('loading');setError(null);setNewImages([]);setImagesToDelete([])
async function load(){
try{const[template,imagePaths]=await Promise.all([getTemplate(templateSlug),getTemplateImages(templateSlug)])
if(requestIdRef.current!==thisRequestId)return
setOriginalTemplate(template);setName(template.name);setDescription(template.description);setDefaultStrict(template.default_strict)
//Build image list with thumbnails
const images:ExistingImage[]=[]
for(const path of imagePaths){const filename=path.split('/').pop()||path
let thumbnailUrl:string|null=null
if(isPyWebView()){try{thumbnailUrl=await bridge.getTemplateImageThumbnail(path)}catch{}}
images.push({path,filename,thumbnailUrl,isPrimary:path===template.primary_image})}
if(requestIdRef.current!==thisRequestId)return
images.sort((a,b)=>(b.isPrimary?1:0)-(a.isPrimary?1:0))
setExistingImages(images);setLoadState('loaded')
}catch(e){if(requestIdRef.current!==thisRequestId)return
const msg=e instanceof Error?e.message:'Failed to load template'
if(msg.toLowerCase().includes('not found')){setLoadState('not-found')}else{setError(msg);setLoadState('error')}}}
load()
return()=>{requestIdRef.current++}},[templateSlug,isActive,getTemplate,getTemplateImages])
//Handle file drop
const handleFilesAdded=useCallback(async(files:File[])=>{
setUploadError(null)
const{processed,rejected}=await processImageFiles(files)
if(rejected.length>0)setUploadError(`Unsupported files: ${rejected.join(', ')}`)
setNewImages(prev=>[...prev,...processed])
},[])
const handleDropError=useCallback((err:Error)=>{setUploadError(err.message||'Failed to add files.')},[])
//Image management handlers
const handleDeleteExisting=(path:string)=>{setImagesToDelete(prev=>[...prev,path]);setExistingImages(prev=>prev.filter(img=>img.path!==path))}
const handleDeleteNew=(index:number)=>setNewImages(prev=>prev.filter((_,i)=>i!==index))
const handleSetPrimary=(path:string)=>{setExistingImages(prev=>prev.map(img=>({...img,isPrimary:img.path===path})).sort((a,b)=>(b.isPrimary?1:0)-(a.isPrimary?1:0)))}
//Save handler
const handleSave=async()=>{if(!name.trim()){toast.error('Please enter a template name');return}
const remainingExisting=existingImages.filter(img=>!imagesToDelete.includes(img.path))
if(remainingExisting.length===0&&newImages.length===0){toast.error('Template must have at least one image');return}
setIsSaving(true)
try{
//Update template metadata
await updateTemplate(templateSlug,name.trim(),description.trim(),defaultStrict)
//Delete removed images
for(const path of imagesToDelete){const filename=path.split('/').pop()||'';await deleteTemplateImage(templateSlug,filename)}
//Upload new images
for(const{file,base64}of newImages){await uploadTemplateImage(templateSlug,file.name,base64)}
//Set primary if changed
const newPrimary=existingImages.find(img=>img.isPrimary&&!imagesToDelete.includes(img.path))
if(newPrimary&&originalTemplate&&newPrimary.path!==originalTemplate.primary_image){const filename=newPrimary.path.split('/').pop()||'';await setPrimaryTemplateImage(templateSlug,filename)}
await refresh()
//Update tab title if name changed
if(name.trim()!==originalTemplate?.name&&tabId){updateTabTitle(tabId,name.trim())}
//Reload to get fresh state
const[template,imagePaths]=await Promise.all([getTemplate(templateSlug),getTemplateImages(templateSlug)])
setOriginalTemplate(template);setName(template.name);setDescription(template.description);setDefaultStrict(template.default_strict)
const images:ExistingImage[]=[]
for(const path of imagePaths){const filename=path.split('/').pop()||path
let thumbnailUrl:string|null=null
if(isPyWebView()){try{thumbnailUrl=await bridge.getTemplateImageThumbnail(path)}catch{}}
images.push({path,filename,thumbnailUrl,isPrimary:path===template.primary_image})}
images.sort((a,b)=>(b.isPrimary?1:0)-(a.isPrimary?1:0))
setExistingImages(images);setNewImages([]);setImagesToDelete([])
toast.success(`Template "${name.trim()}" saved`)
}catch(e){toast.error(e instanceof Error?e.message:'Failed to save template')
}finally{setIsSaving(false)}}
//Delete handler
const handleDelete=async()=>{setIsDeleting(true)
try{await deleteTemplate(templateSlug);if(tabId)closeTab(tabId);toast.success('Template deleted')
}catch(e){toast.error(e instanceof Error?e.message:'Failed to delete template')
}finally{setIsDeleting(false);setShowDeleteConfirm(false)}}
//Reanalyze handler
const handleReanalyze=async()=>{setIsReanalyzing(true)
try{await reanalyzeTemplate(templateSlug)
//Reload template to get updated analysis
const template=await getTemplate(templateSlug)
setOriginalTemplate(template)
toast.success('Template re-analyzed')
}catch(e){toast.error(e instanceof Error?e.message:'Failed to re-analyze template')
}finally{setIsReanalyzing(false)}}
//Retry handler
const handleRetry=()=>{setLoadState('loading');requestIdRef.current++}
//Loading state
if(loadState==='loading')return(<div className="flex-1 flex items-center justify-center"><Loader2 className="w-8 h-8 animate-spin text-muted-foreground/50"/></div>)
//Error state
if(loadState==='error')return(<div className="flex-1 flex flex-col items-center justify-center gap-4"><AlertTriangle className="w-8 h-8 text-destructive/50"/><p className="text-sm text-muted-foreground">{error||'Failed to load template'}</p><Button variant="outline" size="sm" onClick={handleRetry}>Retry</Button></div>)
//Not found state
if(loadState==='not-found')return(<div className="flex-1 flex flex-col items-center justify-center gap-4"><Layout className="w-12 h-12 text-muted-foreground/30"/><p className="text-sm text-muted-foreground">Template not found</p><p className="text-xs text-muted-foreground/60">It may have been deleted</p><Button variant="outline" size="sm" onClick={()=>{if(tabId)closeTab(tabId)}}>Close Tab</Button></div>)
const visibleExistingImages=existingImages.filter(img=>!imagesToDelete.includes(img.path))
const analysis=originalTemplate?.analysis
//Loaded state - inline editing view
return(<div className="flex-1 flex flex-col min-h-0 overflow-hidden">
{/* Header */}
<div className="flex-shrink-0 border-b bg-background/95 backdrop-blur-sm px-6 py-4">
<div className="flex items-center justify-between">
<div className="flex items-center gap-3"><Layout className="w-5 h-5 text-emerald-500"/><h1 className="text-lg font-semibold">{originalTemplate?.name||'Template'}</h1>{isDirty&&<span className="text-blue-500">•</span>}</div>
<div className="flex items-center gap-2">
<Button variant="outline" size="sm" onClick={handleReanalyze} disabled={isReanalyzing||visibleExistingImages.length===0}><RefreshCw className={cn("w-4 h-4 mr-1",isReanalyzing&&"animate-spin")}/>{isReanalyzing?'Analyzing...':'Re-analyze'}</Button>
<Button variant="outline" size="sm" onClick={()=>setShowDeleteConfirm(true)} className="text-destructive hover:text-destructive"><Trash2 className="w-4 h-4 mr-1"/>Delete</Button>
<Button size="sm" onClick={handleSave} disabled={isSaving||!isDirty} className="bg-emerald-600 hover:bg-emerald-700"><Save className="w-4 h-4 mr-1"/>{isSaving?'Saving...':'Save'}</Button>
</div>
</div>
</div>
{/* Content */}
<div className="flex-1 overflow-y-auto p-6">
<div className="max-w-2xl mx-auto space-y-6">
{/* Name */}
<div className="space-y-2">
<label htmlFor="template-name" className="text-sm font-medium">Name <span className="text-red-500">*</span></label>
<Input id="template-name" value={name} onChange={e=>setName(e.target.value)} placeholder="e.g., Hero Banner"/>
</div>
{/* Description */}
<div className="space-y-2">
<label htmlFor="template-desc" className="text-sm font-medium">Description</label>
<textarea id="template-desc" value={description} onChange={e=>setDescription(e.target.value)} placeholder="Describe the template..." rows={3} className="w-full px-3 py-2 text-sm border rounded-md bg-transparent focus:outline-none focus:ring-2 focus:ring-emerald-500 resize-none"/>
</div>
{/* Default Strict Toggle */}
<div className="flex items-center justify-between py-2">
<div className="space-y-0.5"><label htmlFor="default-strict" className="text-sm font-medium">Strictly Follow by Default</label><p className="text-xs text-muted-foreground">When ON, new generations preserve exact layout</p></div>
<button id="default-strict" type="button" role="switch" aria-checked={defaultStrict} onClick={()=>setDefaultStrict(!defaultStrict)} className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 ${defaultStrict?'bg-emerald-600':'bg-gray-200 dark:bg-gray-700'}`}><span className={`pointer-events-none inline-block h-4 w-4 rounded-full bg-white shadow-lg ring-0 transition-transform ${defaultStrict?'translate-x-4':'translate-x-0'}`}/></button>
</div>
{/* Images */}
<div className="space-y-3">
<label className="text-sm font-medium">Template Images <span className="text-red-500">*</span></label>
{uploadError&&<p className="text-sm text-destructive">{uploadError}</p>}
{/* Existing Images */}
{visibleExistingImages.length>0&&(<div className="flex flex-wrap gap-2">
{visibleExistingImages.map(img=>(<div key={img.path} className={cn("relative group rounded-lg overflow-hidden",img.isPrimary?"ring-2 ring-emerald-500 ring-offset-2":"")}>
{img.thumbnailUrl?<img src={img.thumbnailUrl} alt={img.filename} className="h-24 w-24 object-cover"/>:<div className="h-24 w-24 bg-muted flex items-center justify-center"><Loader2 className="w-4 h-4 animate-spin text-muted-foreground"/></div>}
{img.isPrimary&&<div className="absolute top-1 left-1 bg-emerald-500 text-white rounded-full p-0.5"><Star className="h-3 w-3 fill-current"/></div>}
<div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-1">
{!img.isPrimary&&<button type="button" onClick={()=>handleSetPrimary(img.path)} className="h-7 w-7 bg-emerald-500 text-white rounded-full flex items-center justify-center hover:bg-emerald-600" title="Set as primary"><Star className="h-3.5 w-3.5"/></button>}
<button type="button" onClick={()=>handleDeleteExisting(img.path)} className="h-7 w-7 bg-red-500 text-white rounded-full flex items-center justify-center hover:bg-red-600" title="Delete"><X className="h-3.5 w-3.5"/></button>
</div>
<span className="absolute bottom-0 left-0 right-0 bg-black/60 text-white text-[10px] px-1 truncate">{img.filename}</span>
</div>))}
</div>)}
{/* New Images */}
{newImages.length>0&&(<div className="flex flex-wrap gap-2">
{newImages.map((item,i)=>(<div key={i} className="relative group rounded-lg overflow-hidden border-2 border-dashed border-green-500">
<img src={item.dataUrl} alt={item.file.name} className="h-24 w-24 object-cover"/>
<div className="absolute top-1 right-1 bg-green-500 text-white text-[10px] px-1 rounded">NEW</div>
<button type="button" onClick={()=>handleDeleteNew(i)} className="absolute -top-1 -right-1 h-5 w-5 bg-red-500 text-white rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"><X className="h-3 w-3"/></button>
<span className="absolute bottom-0 left-0 right-0 bg-black/60 text-white text-[10px] px-1 truncate">{item.file.name}</span>
</div>))}
</div>)}
{/* Dropzone */}
<Dropzone accept={{'image/*':getAllowedImageExts().map(e=>e)}} maxFiles={20} onDrop={handleFilesAdded} onError={handleDropError} className="border-dashed p-4">
<DropzoneEmptyState><div className="flex flex-col items-center"><Plus className="w-6 h-6 text-muted-foreground mb-1"/><p className="text-xs text-muted-foreground">Drop images or click to add</p></div></DropzoneEmptyState>
</Dropzone>
<p className="text-xs text-muted-foreground">Click the star to set the primary image.</p>
</div>
{/* Analysis Section (read-only, collapsible) */}
{analysis&&(<div className="space-y-3 border-t pt-4">
<button type="button" className="flex items-center gap-2 text-sm font-medium hover:text-emerald-600 transition-colors" onClick={()=>setAnalysisOpen(!analysisOpen)}>
{analysisOpen?<ChevronDown className="w-4 h-4"/>:<ChevronRight className="w-4 h-4"/>}Template Analysis
</button>
{analysisOpen&&<AnalysisDisplay analysis={analysis}/>}
</div>)}
</div>
</div>
{/* Delete Confirmation Dialog */}
<AlertDialog open={showDeleteConfirm} onOpenChange={setShowDeleteConfirm}>
<AlertDialogContent>
<AlertDialogHeader><AlertDialogTitle>Delete Template</AlertDialogTitle><AlertDialogDescription>Are you sure you want to delete "{originalTemplate?.name}"? This action cannot be undone.</AlertDialogDescription></AlertDialogHeader>
<AlertDialogFooter><AlertDialogCancel disabled={isDeleting}>Cancel</AlertDialogCancel><AlertDialogAction onClick={handleDelete} disabled={isDeleting} className="bg-destructive hover:bg-destructive/90">{isDeleting?'Deleting...':'Delete'}</AlertDialogAction></AlertDialogFooter>
</AlertDialogContent>
</AlertDialog>
</div>)}
//Analysis display component (read-only)
function AnalysisDisplay({analysis}:{analysis:TemplateAnalysis}){
if(isV2Analysis(analysis)){
//V2 analysis display
const{canvas,style,layout,copywriting,visual_scene,constraints}=analysis
return(<div className="space-y-4 text-sm">
<div className="grid grid-cols-2 gap-4">
<div><span className="text-muted-foreground">Canvas:</span> {canvas.width}x{canvas.height}</div>
<div><span className="text-muted-foreground">Aspect Ratio:</span> {canvas.aspect_ratio}</div>
</div>
{/* Style */}
{style&&(<div className="space-y-1">
<h4 className="font-medium text-muted-foreground">Style</h4>
<div className="pl-2 space-y-1 text-xs">
{style.palette?.length>0&&<div><span className="text-muted-foreground">Palette:</span> {style.palette.join(', ')}</div>}
{style.lighting&&<div><span className="text-muted-foreground">Lighting:</span> {style.lighting}</div>}
{style.mood&&<div><span className="text-muted-foreground">Mood:</span> {style.mood}</div>}
</div>
</div>)}
{/* Layout */}
{layout&&(<div className="space-y-1">
<h4 className="font-medium text-muted-foreground">Layout</h4>
<div className="pl-2 space-y-1 text-xs">
<div><span className="text-muted-foreground">Structure:</span> {layout.structure}</div>
{layout.zones.length>0&&<div><span className="text-muted-foreground">Zones:</span> {layout.zones.join(', ')}</div>}
<div><span className="text-muted-foreground">Hierarchy:</span> {layout.hierarchy}</div>
</div>
</div>)}
{/* Copywriting */}
{copywriting&&(<div className="space-y-1">
<h4 className="font-medium text-muted-foreground">Copywriting</h4>
<div className="pl-2 space-y-1 text-xs">
{copywriting.headline&&<div><span className="text-muted-foreground">Headline:</span> {copywriting.headline}</div>}
{copywriting.subheadline&&<div><span className="text-muted-foreground">Subheadline:</span> {copywriting.subheadline}</div>}
{copywriting.cta&&<div><span className="text-muted-foreground">CTA:</span> {copywriting.cta}</div>}
{copywriting.benefits.length>0&&<div><span className="text-muted-foreground">Benefits:</span> {copywriting.benefits.join(', ')}</div>}
</div>
</div>)}
{/* Visual Scene */}
{visual_scene&&(<div className="space-y-1">
<h4 className="font-medium text-muted-foreground">Visual Scene</h4>
<div className="pl-2 space-y-1 text-xs">
{visual_scene.scene_description&&<div><span className="text-muted-foreground">Scene:</span> {visual_scene.scene_description}</div>}
{visual_scene.product_placement&&<div><span className="text-muted-foreground">Product Placement:</span> {visual_scene.product_placement}</div>}
{visual_scene.photography_style&&<div><span className="text-muted-foreground">Photography Style:</span> {visual_scene.photography_style}</div>}
</div>
</div>)}
{/* Constraints */}
{constraints&&(<div className="space-y-1">
<h4 className="font-medium text-muted-foreground">Constraints</h4>
<div className="pl-2 space-y-1 text-xs">
{constraints.non_negotiables.length>0&&<div><span className="text-muted-foreground">Non-Negotiables:</span> {constraints.non_negotiables.join(', ')}</div>}
{constraints.creative_freedom.length>0&&<div><span className="text-muted-foreground">Creative Freedom:</span> {constraints.creative_freedom.join(', ')}</div>}
{constraints.product_integration&&<div><span className="text-muted-foreground">Product Integration:</span> {constraints.product_integration}</div>}
</div>
</div>)}
</div>)
}else{
//V1 analysis display
const{canvas,message,style,elements,product_slot}=analysis
return(<div className="space-y-4 text-sm">
<div className="grid grid-cols-2 gap-4">
<div><span className="text-muted-foreground">Canvas:</span> {canvas.width}x{canvas.height}</div>
<div><span className="text-muted-foreground">Aspect Ratio:</span> {canvas.aspect_ratio}</div>
</div>
{/* Message */}
{message&&(<div className="space-y-1">
<h4 className="font-medium text-muted-foreground">Message</h4>
<div className="pl-2 space-y-1 text-xs">
{message.intent&&<div><span className="text-muted-foreground">Intent:</span> {message.intent}</div>}
{message.audience&&<div><span className="text-muted-foreground">Audience:</span> {message.audience}</div>}
{message.key_claims?.length>0&&<div><span className="text-muted-foreground">Key Claims:</span> {message.key_claims.join(', ')}</div>}
</div>
</div>)}
{/* Style */}
{style&&(<div className="space-y-1">
<h4 className="font-medium text-muted-foreground">Style</h4>
<div className="pl-2 space-y-1 text-xs">
{style.palette?.length>0&&<div><span className="text-muted-foreground">Palette:</span> {style.palette.join(', ')}</div>}
{style.lighting&&<div><span className="text-muted-foreground">Lighting:</span> {style.lighting}</div>}
{style.mood&&<div><span className="text-muted-foreground">Mood:</span> {style.mood}</div>}
</div>
</div>)}
{/* Elements */}
{elements&&elements.length>0&&(<div className="space-y-1">
<h4 className="font-medium text-muted-foreground">Layout Elements ({elements.length})</h4>
<div className="pl-2 text-xs text-muted-foreground/80">{elements.map(e=>e.type).join(', ')}</div>
</div>)}
{/* Product Slot */}
{product_slot&&(<div className="space-y-1">
<h4 className="font-medium text-muted-foreground">Product Slot</h4>
<div className="pl-2 text-xs"><span className="text-muted-foreground">Position:</span> ({product_slot.geometry.x}, {product_slot.geometry.y}) - {product_slot.geometry.width}x{product_slot.geometry.height}</div>
</div>)}
</div>)}}
