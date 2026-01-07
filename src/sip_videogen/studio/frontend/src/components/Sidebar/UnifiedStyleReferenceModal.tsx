//UnifiedStyleReferenceModal - Combined view/edit modal with inline editing
import{useState,useEffect,useCallback,useMemo}from'react'
import{Layout,Loader2,Check,Circle,Lock,Unlock,Pencil,Trash2,X,Star,RefreshCw,Save,ImagePlus}from'lucide-react'
import{Button}from'@/components/ui/button'
import{Input}from'@/components/ui/input'
import{Dialog,DialogContent,DialogHeader,DialogTitle}from'@/components/ui/dialog'
import{Dropzone,DropzoneEmptyState}from'@/components/ui/dropzone'
import{useStyleReferences}from'@/context/StyleReferenceContext'
import{bridge,isPyWebView,isV2StyleReferenceAnalysis,isV3StyleReferenceAnalysis}from'@/lib/bridge'
import{processImageFiles}from'@/lib/file-utils'
import{getAllowedImageExts}from'@/lib/constants'
import{toast}from'@/components/ui/toaster'
import type{StyleReferenceFull,StyleReferenceAnalysisV2,StyleReferenceAnalysisV3}from'@/lib/bridge'
import type{ProcessedFile}from'@/lib/file-utils'
interface ExistingImage{path:string;filename:string;thumbnailUrl:string|null;isPrimary:boolean}
interface UnifiedStyleReferenceModalProps{open:boolean;onOpenChange:(open:boolean)=>void;styleRefSlug:string;initialMode?:'view'|'edit';onDelete?:(slug:string)=>void}
//Info row for label-value pairs
function InfoRow({label,value}:{label:string;value:string|undefined|null}){if(!value)return null;return(<div className="flex justify-between gap-2"><span className="text-xs text-neutral-500 dark:text-neutral-400 shrink-0">{label}</span><span className="text-sm text-neutral-900 dark:text-neutral-100 text-right">{value}</span></div>)}
//Color swatch component
function ColorSwatch({color}:{color:string}){return(<div className="w-7 h-7 rounded-md border border-neutral-200 dark:border-neutral-700 shadow-sm" style={{backgroundColor:color}} title={color}/>)}
//Section wrapper
function Section({title,children}:{title:string;children:React.ReactNode}){return(<div className="space-y-2"><h3 className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">{title}</h3>{children}</div>)}
//Card wrapper for info content
function InfoCard({children}:{children:React.ReactNode}){return(<div className="bg-neutral-100 dark:bg-neutral-800 rounded-md p-3 space-y-1.5">{children}</div>)}
export function UnifiedStyleReferenceModal({open,onOpenChange,styleRefSlug,initialMode='view',onDelete}:UnifiedStyleReferenceModalProps){
const{getStyleReference,getStyleReferenceImages,updateStyleReference,uploadStyleReferenceImage,deleteStyleReferenceImage,setPrimaryStyleReferenceImage,reanalyzeStyleReference,attachStyleReference,detachStyleReference,setStyleReferenceStrictness,attachedStyleReferences,refresh}=useStyleReferences()
//Core state
const[mode,setMode]=useState<'view'|'edit'>(initialMode)
const[styleRef,setStyleRef]=useState<StyleReferenceFull|null>(null)
const[imageSrc,setImageSrc]=useState<string|null>(null)
const[isLoading,setIsLoading]=useState(true)
const[error,setError]=useState<string|null>(null)
//Edit state
const[editName,setEditName]=useState('')
const[editDescription,setEditDescription]=useState('')
const[editDefaultStrict,setEditDefaultStrict]=useState(true)
const[existingImages,setExistingImages]=useState<ExistingImage[]>([])
const[newImages,setNewImages]=useState<ProcessedFile[]>([])
const[imagesToDelete,setImagesToDelete]=useState<string[]>([])
const[isSaving,setIsSaving]=useState(false)
const[isReanalyzing,setIsReanalyzing]=useState(false)
const[uploadError,setUploadError]=useState<string|null>(null)
//Check attachment status
const attached=attachedStyleReferences.find(a=>a.style_reference_slug===styleRefSlug)
const isAttached=!!attached
const isStrict=attached?.strict??false
//Compute hasChanges
const hasChanges=useMemo(()=>{if(!styleRef)return false;return editName.trim()!==styleRef.name||editDescription.trim()!==styleRef.description||editDefaultStrict!==styleRef.default_strict||newImages.length>0||imagesToDelete.length>0||existingImages.some(img=>img.isPrimary&&img.path!==styleRef.primary_image)},[styleRef,editName,editDescription,editDefaultStrict,newImages,imagesToDelete,existingImages])
//Load style reference data
useEffect(()=>{if(!open||!styleRefSlug)return
let cancelled=false
async function load(){setIsLoading(true);setError(null);setImageSrc(null)
try{const[sr,imagePaths]=await Promise.all([getStyleReference(styleRefSlug),getStyleReferenceImages(styleRefSlug)])
if(cancelled)return
setStyleRef(sr);setEditName(sr.name);setEditDescription(sr.description);setEditDefaultStrict(sr.default_strict)
//Load images for edit mode
const imgs:ExistingImage[]=[]
for(const path of imagePaths){const filename=path.split('/').pop()||path
let thumbnailUrl:string|null=null
if(isPyWebView()){try{thumbnailUrl=await bridge.getStyleReferenceImageThumbnail(path)}catch{}}
imgs.push({path,filename,thumbnailUrl,isPrimary:path===sr.primary_image})}
if(!cancelled){imgs.sort((a,b)=>(b.isPrimary?1:0)-(a.isPrimary?1:0));setExistingImages(imgs)}
//Load full image for view
if(isPyWebView()&&sr.primary_image){try{const url=await bridge.getStyleReferenceImageFull(sr.primary_image);if(!cancelled)setImageSrc(url)}catch{}}}
catch(err){if(!cancelled)setError(err instanceof Error?err.message:'Failed to load')}
finally{if(!cancelled)setIsLoading(false)}}
load();return()=>{cancelled=true}},[open,styleRefSlug,getStyleReference,getStyleReferenceImages])
//Reset mode when opening
useEffect(()=>{if(open){setMode(initialMode);setNewImages([]);setImagesToDelete([]);setUploadError(null)}},[open,initialMode])
//Handlers
const handleClose=useCallback(()=>{if(isSaving||isReanalyzing)return;if(mode==='edit'&&hasChanges){if(!confirm('Discard unsaved changes?'))return};onOpenChange(false)},[isSaving,isReanalyzing,mode,hasChanges,onOpenChange])
const handleAttach=()=>attachStyleReference(styleRefSlug)
const handleDetach=()=>detachStyleReference(styleRefSlug)
const handleToggleStrict=()=>setStyleReferenceStrictness(styleRefSlug,!isStrict)
const handleDelete=()=>{if(confirm(`Delete style reference "${styleRef?.name}"? This cannot be undone.`)){handleClose();onDelete?.(styleRefSlug)}}
const handleEnterEdit=()=>{setMode('edit');setUploadError(null)}
const handleCancelEdit=()=>{if(hasChanges&&!confirm('Discard unsaved changes?'))return;setMode('view');setEditName(styleRef?.name||'');setEditDescription(styleRef?.description||'');setEditDefaultStrict(styleRef?.default_strict??true);setNewImages([]);setImagesToDelete([]);setExistingImages(prev=>prev.map(img=>({...img,isPrimary:img.path===styleRef?.primary_image})).sort((a,b)=>(b.isPrimary?1:0)-(a.isPrimary?1:0)));setUploadError(null)}
//Image handlers
const handleFilesAdded=useCallback(async(files:File[])=>{setUploadError(null)
const{processed,rejected}=await processImageFiles(files)
if(rejected.length>0)setUploadError(`Unsupported: ${rejected.join(', ')}`)
const totalExisting=existingImages.filter(img=>!imagesToDelete.includes(img.path)).length
const remaining=2-totalExisting-newImages.length
if(remaining<=0){setUploadError('Max 2 images allowed.');return}
if(processed.length>remaining){setUploadError('Max 2 images allowed.');setNewImages(prev=>[...prev,...processed.slice(0,remaining)])}
else setNewImages(prev=>[...prev,...processed])},[existingImages,imagesToDelete,newImages.length])
const handleDeleteExisting=(path:string)=>{setImagesToDelete(prev=>[...prev,path]);setExistingImages(prev=>prev.filter(img=>img.path!==path))}
const handleDeleteNew=(idx:number)=>setNewImages(prev=>prev.filter((_,i)=>i!==idx))
const handleSetPrimary=(path:string)=>{setExistingImages(prev=>prev.map(img=>({...img,isPrimary:img.path===path})).sort((a,b)=>(b.isPrimary?1:0)-(a.isPrimary?1:0)))}
//Save handler
const handleSave=async()=>{if(!editName.trim()){toast.error('Please enter a name');return}
const remainingExisting=existingImages.filter(img=>!imagesToDelete.includes(img.path))
if(remainingExisting.length===0&&newImages.length===0){toast.error('At least one image required');return}
setIsSaving(true)
try{await updateStyleReference(styleRefSlug,editName.trim(),editDescription.trim(),editDefaultStrict)
for(const path of imagesToDelete){const fn=path.split('/').pop()||'';await deleteStyleReferenceImage(styleRefSlug,fn)}
for(const{file,base64}of newImages){await uploadStyleReferenceImage(styleRefSlug,file.name,base64)}
const newPrimary=existingImages.find(img=>img.isPrimary&&!imagesToDelete.includes(img.path))
if(newPrimary&&styleRef&&newPrimary.path!==styleRef.primary_image){const fn=newPrimary.path.split('/').pop()||'';await setPrimaryStyleReferenceImage(styleRefSlug,fn)}
await refresh();toast.success('Style reference updated')
//Reload to get updated data
const updatedSr=await getStyleReference(styleRefSlug);setStyleRef(updatedSr);setEditName(updatedSr.name);setEditDescription(updatedSr.description);setEditDefaultStrict(updatedSr.default_strict)
setNewImages([]);setImagesToDelete([]);setMode('view')}
catch(err){toast.error(err instanceof Error?err.message:'Failed to save')}
finally{setIsSaving(false)}}
//Reanalyze handler
const handleReanalyze=async()=>{if(isReanalyzing)return;setIsReanalyzing(true)
try{const analysis=await reanalyzeStyleReference(styleRefSlug);setStyleRef(prev=>prev?{...prev,analysis}:prev);toast.success('Reanalyzed successfully')}
catch(err){toast.error(err instanceof Error?err.message:'Reanalyze failed')}
finally{setIsReanalyzing(false)}}
//Get analysis version
const analysis=styleRef?.analysis
const v2=analysis&&isV2StyleReferenceAnalysis(analysis)?analysis as StyleReferenceAnalysisV2:null
const v3=analysis&&isV3StyleReferenceAnalysis(analysis)?analysis as StyleReferenceAnalysisV3:null
const visibleExistingImages=existingImages.filter(img=>!imagesToDelete.includes(img.path))
const canAddImages=visibleExistingImages.length+newImages.length<2
const isWorking=isSaving||isReanalyzing
return(<Dialog open={open} onOpenChange={handleClose}><DialogContent className="max-w-3xl max-h-[85vh] overflow-hidden">
<DialogHeader><DialogTitle className="flex items-center gap-2">
<Layout className="h-5 w-5 text-brand-500"/>
<span>{mode==='edit'?'Edit Style Reference':styleRef?.name||'Style Reference'}</span>
</DialogTitle></DialogHeader>
{isLoading?(<div className="flex items-center justify-center py-12"><Loader2 className="h-6 w-6 animate-spin text-brand-500"/></div>):error?(<div className="text-sm text-destructive py-4">{error}</div>):(
<div className="grid grid-cols-[260px_1fr] gap-6">
{/*Left Column*/}
<div className="space-y-4">
{mode==='edit'?(
//Edit Mode: Image management in left column
<>
{/*Image Gallery*/}
<div className="space-y-3">
<label className="text-sm font-medium text-neutral-900 dark:text-neutral-100">Reference Images <span className="text-xs text-muted-foreground">(1-2)</span></label>
{uploadError&&<p className="text-xs text-destructive">{uploadError}</p>}
{/*Grid of images*/}
<div className="grid grid-cols-2 gap-2">
{visibleExistingImages.map(img=>(<div key={img.path} className={`relative group aspect-square rounded-lg overflow-hidden border-2 ${img.isPrimary?'border-brand-500':'border-neutral-200 dark:border-neutral-700'}`}>
{img.thumbnailUrl?(<img src={img.thumbnailUrl} alt={img.filename} className="w-full h-full object-cover"/>):(<div className="w-full h-full bg-neutral-100 dark:bg-neutral-800 flex items-center justify-center"><Loader2 className="h-5 w-5 animate-spin text-neutral-400"/></div>)}
{img.isPrimary&&(<div className="absolute top-1.5 left-1.5 bg-brand-500 text-white rounded-full p-1"><Star className="h-3 w-3 fill-current"/></div>)}
<div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2">
{!img.isPrimary&&(<button type="button" onClick={()=>handleSetPrimary(img.path)} className="h-8 w-8 bg-white/90 text-brand-500 rounded-full flex items-center justify-center hover:bg-white" title="Set as primary"><Star className="h-4 w-4"/></button>)}
<button type="button" onClick={()=>handleDeleteExisting(img.path)} className="h-8 w-8 bg-white/90 text-destructive rounded-full flex items-center justify-center hover:bg-white" title="Remove"><X className="h-4 w-4"/></button></div>
</div>))}
{/*New images*/}
{newImages.map((item,idx)=>(<div key={`new-${idx}`} className="relative group aspect-square rounded-lg overflow-hidden border-2 border-dashed border-success">
<img src={item.dataUrl} alt={item.file.name} className="w-full h-full object-cover"/>
<div className="absolute top-1.5 right-1.5 bg-success text-white text-[10px] font-medium px-1.5 py-0.5 rounded">NEW</div>
<button type="button" onClick={()=>handleDeleteNew(idx)} className="absolute top-1.5 left-1.5 h-6 w-6 bg-destructive text-white rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"><X className="h-3 w-3"/></button>
</div>))}
{/*Add more dropzone*/}
{canAddImages&&(<Dropzone accept={{'image/*':getAllowedImageExts()}} maxFiles={2-visibleExistingImages.length-newImages.length} onDrop={handleFilesAdded} onError={e=>setUploadError(e.message)} className="aspect-square border-2 border-dashed border-neutral-300 dark:border-neutral-600 rounded-lg hover:border-brand-500 hover:bg-brand-500/5 transition-colors">
<DropzoneEmptyState><div className="flex flex-col items-center gap-1"><ImagePlus className="h-6 w-6 text-neutral-400"/><span className="text-xs text-neutral-500">Add image</span></div></DropzoneEmptyState></Dropzone>)}
</div>
<p className="text-xs text-muted-foreground">Star = primary image shown in lists</p>
</div>
{/*Action Buttons*/}
<div className="flex gap-2 pt-2 border-t border-neutral-200 dark:border-neutral-700">
<Button variant="outline" size="sm" className="flex-1" onClick={handleCancelEdit} disabled={isWorking}>Cancel</Button>
<Button size="sm" className="flex-1 bg-brand-500 hover:bg-brand-600 gap-1.5" onClick={handleSave} disabled={isWorking||!hasChanges}>{isSaving?<Loader2 className="h-3.5 w-3.5 animate-spin"/>:<Save className="h-3.5 w-3.5"/>}Save</Button>
</div>
</>
):(
//View Mode: Large image preview + attach controls
<>
{/*Reference Image*/}
<div className="aspect-square rounded-lg overflow-hidden bg-neutral-100 dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700">
{imageSrc?(<img src={imageSrc} alt={styleRef?.name} className="w-full h-full object-cover"/>):(<div className="w-full h-full flex items-center justify-center"><Layout className="h-12 w-12 text-neutral-400"/></div>)}</div>
{/*Aspect Ratio Badge*/}
{analysis?.canvas?.aspect_ratio&&(<div className="flex items-center gap-2"><span className="text-xs text-neutral-500 dark:text-neutral-400">Aspect Ratio:</span><span className="text-sm font-medium text-neutral-900 dark:text-neutral-100">{analysis.canvas.aspect_ratio}</span></div>)}
{/*Attach Controls*/}
<div className="space-y-2">
{isAttached?(<><Button variant="outline" size="sm" className="w-full justify-start gap-2" onClick={handleToggleStrict}>{isStrict?<><Lock className="h-4 w-4 text-brand-500"/>Strictly Following</>:<><Unlock className="h-4 w-4"/>Allow Variation</>}</Button>
<Button variant="ghost" size="sm" className="w-full justify-start text-neutral-500" onClick={handleDetach}>Detach from Chat</Button></>):(<Button variant="default" size="sm" className="w-full bg-brand-500 hover:bg-brand-600" onClick={handleAttach}>Attach to Chat</Button>)}</div>
{/*Action Buttons*/}
<div className="flex gap-2 pt-2 border-t border-neutral-200 dark:border-neutral-700">
<Button variant="outline" size="sm" className="flex-1 gap-1.5" onClick={handleEnterEdit}><Pencil className="h-3.5 w-3.5"/>Edit</Button>
<Button variant="outline" size="sm" className="text-destructive hover:text-destructive hover:bg-destructive/10 gap-1.5" onClick={handleDelete}><Trash2 className="h-3.5 w-3.5"/>Delete</Button></div>
</>
)}
</div>
{/*Right Column*/}
<div className="space-y-4 overflow-y-auto max-h-[60vh] p-1 -m-1">
{mode==='edit'?(
//Edit Mode: Form fields
<>
{/*Name Input*/}
<div className="space-y-2"><label className="text-sm font-medium">Name <span className="text-destructive">*</span></label>
<Input value={editName} onChange={e=>setEditName(e.target.value)} placeholder="e.g., Hero Banner Style" autoFocus/></div>
{/*Description*/}
<div className="space-y-2"><label className="text-sm font-medium">Description</label>
<textarea value={editDescription} onChange={e=>setEditDescription(e.target.value)} placeholder="Describe the visual style and key elements" rows={4} className="w-full px-3 py-2 text-sm border border-neutral-200 dark:border-neutral-700 rounded-md bg-transparent focus:outline-none focus:ring-2 focus:ring-brand-500 resize-y min-h-[80px]"/></div>
{/*Default Strict Toggle*/}
<div className="flex items-center justify-between py-3 px-3 bg-neutral-50 dark:bg-neutral-800/50 rounded-lg">
<div className="space-y-0.5"><label className="text-sm font-medium">Strictly Follow by Default</label><p className="text-xs text-muted-foreground">New generations preserve exact style</p></div>
<button type="button" role="switch" aria-checked={editDefaultStrict} onClick={()=>setEditDefaultStrict(!editDefaultStrict)} className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors ${editDefaultStrict?'bg-brand-500':'bg-neutral-300 dark:bg-neutral-600'}`}><span className={`pointer-events-none inline-block h-5 w-5 rounded-full bg-white shadow-lg transition-transform ${editDefaultStrict?'translate-x-5':'translate-x-0'}`}/></button></div>
{/*Analysis Summary Card*/}
{styleRef?.analysis&&(<div className="bg-neutral-50 dark:bg-neutral-800/50 rounded-lg p-4 space-y-3">
<div className="flex items-center justify-between">
<span className="text-sm font-medium">Style Analysis</span>
<Button variant="outline" size="sm" onClick={handleReanalyze} disabled={isWorking} className="h-7 text-xs gap-1.5">{isReanalyzing?<Loader2 className="h-3 w-3 animate-spin"/>:<RefreshCw className="h-3 w-3"/>}Reanalyze</Button></div>
<div className="text-xs text-muted-foreground space-y-1">
{v3?(<><div><span className="font-medium">Version:</span> V3 Color Grading DNA</div><div><span className="font-medium">Film Look:</span> {v3.color_grading?.film_stock_reference||'N/A'}</div>{v3.color_grading?.color_temperature&&<div><span className="font-medium">Temperature:</span> {v3.color_grading.color_temperature}</div>}</>):v2?(<><div><span className="font-medium">Version:</span> V2 Semantic</div><div><span className="font-medium">Mood:</span> {v2.style?.mood||'N/A'}</div>{v2.style?.lighting&&<div><span className="font-medium">Lighting:</span> {v2.style.lighting}</div>}</>):(<><div><span className="font-medium">Version:</span> V1 Legacy</div><div><span className="font-medium">Elements:</span> {(analysis as any).elements?.length||0}</div></>)}
</div>
<p className="text-[10px] text-muted-foreground/70">Click Reanalyze to refresh AI analysis</p></div>)}
</>
):(
//View Mode: Full Analysis Display
<>{v3?(<>
{/*Color Grading DNA - PRIMARY section*/}
<Section title="Color Grading DNA"><InfoCard>
{v3.color_grading?.film_stock_reference&&<InfoRow label="Film Look" value={v3.color_grading.film_stock_reference}/>}
<InfoRow label="Temperature" value={v3.color_grading?.color_temperature}/>
<InfoRow label="Shadows" value={v3.color_grading?.shadow_tint}/>
<InfoRow label="Black Point" value={v3.color_grading?.black_point}/>
<InfoRow label="Highlights" value={v3.color_grading?.highlight_rolloff}/>
<InfoRow label="Highlight Tint" value={v3.color_grading?.highlight_tint}/>
<InfoRow label="Saturation" value={v3.color_grading?.saturation_level}/>
<InfoRow label="Contrast" value={v3.color_grading?.contrast_character}/>
{v3.color_grading?.signature_elements?.length>0&&(<div className="pt-1"><span className="text-xs text-neutral-500 dark:text-neutral-400">Signature Elements:</span><p className="text-sm text-neutral-900 dark:text-neutral-100 mt-0.5">{v3.color_grading.signature_elements.join(' • ')}</p></div>)}
</InfoCard></Section>
{/*Style Suggestions - secondary*/}
{(v3.style_suggestions?.mood||v3.style_suggestions?.environment_tendency||v3.style_suggestions?.lighting_setup)&&(
<Section title="Style Suggestions"><InfoCard>
<InfoRow label="Mood" value={v3.style_suggestions?.mood}/>
<InfoRow label="Environment" value={v3.style_suggestions?.environment_tendency}/>
<InfoRow label="Lighting" value={v3.style_suggestions?.lighting_setup}/>
</InfoCard></Section>)}
</>):v2?(<>
{/*Visual Style*/}
<Section title="Visual Style"><InfoCard>
<InfoRow label="Mood" value={v2.style?.mood}/>
<InfoRow label="Lighting" value={v2.style?.lighting}/>
<InfoRow label="Photography" value={v2.visual_scene?.photography_style}/>
{v2.style?.materials?.length>0&&(<div className="pt-1"><span className="text-xs text-neutral-500 dark:text-neutral-400">Materials:</span><p className="text-sm text-neutral-900 dark:text-neutral-100 mt-0.5">{v2.style.materials.join(' • ')}</p></div>)}
</InfoCard></Section>
{/*Color Palette*/}
{v2.style?.palette?.length>0&&(<Section title="Color Palette"><div className="flex gap-2 flex-wrap">{v2.style.palette.map((c,i)=><ColorSwatch key={i} color={c}/>)}</div></Section>)}
{/*Composition*/}
<Section title="Composition"><InfoCard>
<InfoRow label="Structure" value={v2.layout?.structure}/>
<InfoRow label="Hierarchy" value={v2.layout?.hierarchy}/>
<InfoRow label="Alignment" value={v2.layout?.alignment}/>
{v2.layout?.zones?.length>0&&(<div className="pt-1"><span className="text-xs text-neutral-500 dark:text-neutral-400">Zones:</span><p className="text-sm text-neutral-900 dark:text-neutral-100 mt-0.5">{v2.layout.zones.join(' • ')}</p></div>)}
</InfoCard></Section>
{/*Visual Scene*/}
{v2.visual_scene?.scene_description&&(<Section title="Scene"><InfoCard><p className="text-sm text-neutral-900 dark:text-neutral-100">{v2.visual_scene.scene_description}</p>
{v2.visual_scene?.product_placement&&(<InfoRow label="Product Placement" value={v2.visual_scene.product_placement}/>)}
{v2.visual_scene?.lifestyle_elements?.length>0&&(<div className="pt-1"><span className="text-xs text-neutral-500 dark:text-neutral-400">Lifestyle Elements:</span><p className="text-sm text-neutral-900 dark:text-neutral-100 mt-0.5">{v2.visual_scene.lifestyle_elements.join(' • ')}</p></div>)}
{v2.visual_scene?.visual_treatments?.length>0&&(<div className="pt-1"><span className="text-xs text-neutral-500 dark:text-neutral-400">Visual Treatments:</span><p className="text-sm text-neutral-900 dark:text-neutral-100 mt-0.5">{v2.visual_scene.visual_treatments.join(' • ')}</p></div>)}
</InfoCard></Section>)}
{/*Constraints*/}
{(v2.constraints?.non_negotiables?.length>0||v2.constraints?.creative_freedom?.length>0)&&(<Section title="Constraints"><div className="space-y-3">
{v2.constraints?.non_negotiables?.length>0&&(<div><span className="text-xs font-medium text-brand-600 dark:text-brand-500">Must Preserve</span><ul className="mt-1 space-y-1">{v2.constraints.non_negotiables.map((item,i)=>(<li key={i} className="text-xs flex items-start gap-1.5 text-neutral-900 dark:text-neutral-100"><Check className="h-3 w-3 text-brand-500 mt-0.5 shrink-0"/>{item}</li>))}</ul></div>)}
{v2.constraints?.creative_freedom?.length>0&&(<div><span className="text-xs font-medium text-neutral-500">Can Vary</span><ul className="mt-1 space-y-1">{v2.constraints.creative_freedom.map((item,i)=>(<li key={i} className="text-xs flex items-start gap-1.5 text-neutral-500 dark:text-neutral-400"><Circle className="h-3 w-3 mt-0.5 shrink-0"/>{item}</li>))}</ul></div>)}
{v2.constraints?.product_integration&&(<div className="pt-2"><span className="text-xs text-neutral-500 dark:text-neutral-400">Product Integration:</span><p className="text-sm text-neutral-900 dark:text-neutral-100 mt-0.5">{v2.constraints.product_integration}</p></div>)}
</div></Section>)}
</>):analysis?(
//V1 Fallback
<Section title="Analysis (V1)"><InfoCard>
<InfoRow label="Version" value="1.0 (Legacy)"/>
<InfoRow label="Aspect Ratio" value={analysis.canvas?.aspect_ratio}/>
<InfoRow label="Background" value={analysis.canvas?.background}/>
{'style' in analysis&&analysis.style&&(<><InfoRow label="Mood" value={(analysis as any).style.mood}/><InfoRow label="Lighting" value={(analysis as any).style.lighting}/></>)}
{'elements' in analysis&&(<InfoRow label="Elements" value={`${(analysis as any).elements?.length||0} defined`}/>)}
{'product_slot' in analysis&&(<InfoRow label="Product Slot" value={(analysis as any).product_slot?'Yes':'No'}/>)}
</InfoCard></Section>):(<div className="text-sm text-neutral-500 py-4">No analysis data. Click Edit to add images.</div>)}</>)}
</div>
</div>
)}</DialogContent></Dialog>)}
