//EditStyleReferenceDialog for editing existing style references
import{useState,useEffect,useCallback}from'react'
import{Layout,X,Star,Loader2,RefreshCw}from'lucide-react'
import{Button}from'@/components/ui/button'
import{FormDialog}from'@/components/ui/form-dialog'
import{Input}from'@/components/ui/input'
import{Dropzone,DropzoneEmptyState}from'@/components/ui/dropzone'
import{useStyleReferences}from'@/context/StyleReferenceContext'
import{useAsyncAction}from'@/hooks/useAsyncAction'
import{processImageFiles}from'@/lib/file-utils'
import type{ProcessedFile}from'@/lib/file-utils'
import{bridge,isPyWebView,isV2StyleReferenceAnalysis}from'@/lib/bridge'
import{getAllowedImageExts}from'@/lib/constants'
import{toast}from'@/components/ui/toaster'
import type{StyleReferenceFull}from'@/lib/bridge'
interface ExistingImage{path:string;filename:string;thumbnailUrl:string|null;isPrimary:boolean}
interface EditStyleReferenceDialogProps{open:boolean;onOpenChange:(open:boolean)=>void;styleRefSlug:string}
export function EditStyleReferenceDialog({open,onOpenChange,styleRefSlug}:EditStyleReferenceDialogProps){
const{getStyleReference,getStyleReferenceImages,updateStyleReference,uploadStyleReferenceImage,deleteStyleReferenceImage,setPrimaryStyleReferenceImage,reanalyzeStyleReference,refresh}=useStyleReferences()
const[name,setName]=useState('')
const[description,setDescription]=useState('')
const[defaultStrict,setDefaultStrict]=useState(true)
const[existingImages,setExistingImages]=useState<ExistingImage[]>([])
const[newImages,setNewImages]=useState<ProcessedFile[]>([])
const[imagesToDelete,setImagesToDelete]=useState<string[]>([])
const[isLoading,setIsLoading]=useState(true)
const[loadError,setLoadError]=useState<string|null>(null)
const[originalStyleRef,setOriginalStyleRef]=useState<StyleReferenceFull|null>(null)
const[uploadError,setUploadError]=useState<string|null>(null)
const[isReanalyzing,setIsReanalyzing]=useState(false)
//Load style reference data when dialog opens
useEffect(()=>{if(!open||!styleRefSlug)return
let cancelled=false
async function load(){setIsLoading(true);setLoadError(null);setNewImages([]);setImagesToDelete([])
try{const[sr,imagePaths]=await Promise.all([getStyleReference(styleRefSlug),getStyleReferenceImages(styleRefSlug)])
if(cancelled)return
setOriginalStyleRef(sr);setName(sr.name);setDescription(sr.description);setDefaultStrict(sr.default_strict)
const images:ExistingImage[]=[]
for(const path of imagePaths){const filename=path.split('/').pop()||path
let thumbnailUrl:string|null=null
if(isPyWebView()){try{thumbnailUrl=await bridge.getStyleReferenceImageThumbnail(path)}catch{}}
images.push({path,filename,thumbnailUrl,isPrimary:path===sr.primary_image})}
if(!cancelled){images.sort((a,b)=>(b.isPrimary?1:0)-(a.isPrimary?1:0));setExistingImages(images)}
}catch(err){if(!cancelled)setLoadError(err instanceof Error?err.message:'Failed to load style reference')
}finally{if(!cancelled)setIsLoading(false)}}
load();return()=>{cancelled=true}},[open,styleRefSlug,getStyleReference,getStyleReferenceImages])
const handleFilesAdded=useCallback(async(files:File[])=>{
setUploadError(null)
const{processed,rejected}=await processImageFiles(files)
if(rejected.length>0)setUploadError(`Unsupported files: ${rejected.join(', ')}`)
//Limit to 2 images max total
const totalExisting=existingImages.filter(img=>!imagesToDelete.includes(img.path)).length
const totalNew=newImages.length
const remaining=2-totalExisting-totalNew
if(remaining<=0){setUploadError('Style references allow max 2 images.');return}
if(processed.length>remaining){
setUploadError(prev=>prev?prev+' Max 2 images.':'Max 2 images.')
setNewImages(prev=>[...prev,...processed.slice(0,remaining)])}
else setNewImages(prev=>[...prev,...processed])},[existingImages,imagesToDelete,newImages.length])
const handleDropError=useCallback((err:Error)=>{setUploadError(err.message||'Failed to add files.')},[])
const handleDeleteExisting=(path:string)=>{setImagesToDelete(prev=>[...prev,path]);setExistingImages(prev=>prev.filter(img=>img.path!==path))}
const handleDeleteNew=(index:number)=>setNewImages(prev=>prev.filter((_,i)=>i!==index))
const handleSetPrimary=(path:string)=>{setExistingImages(prev=>prev.map(img=>({...img,isPrimary:img.path===path})).sort((a,b)=>(b.isPrimary?1:0)-(a.isPrimary?1:0)))}
const{execute:save,isLoading:isSaving,error:saveError,clearError}=useAsyncAction(async()=>{
if(!name.trim())throw new Error('Please enter a style reference name.')
const remainingExisting=existingImages.filter(img=>!imagesToDelete.includes(img.path))
if(remainingExisting.length===0&&newImages.length===0)throw new Error('Style reference must have at least one image.')
if(remainingExisting.length+newImages.length>2)throw new Error('Style references allow max 2 images.')
await updateStyleReference(styleRefSlug,name.trim(),description.trim(),defaultStrict)
for(const path of imagesToDelete){const filename=path.split('/').pop()||'';await deleteStyleReferenceImage(styleRefSlug,filename)}
for(const{file,base64}of newImages){await uploadStyleReferenceImage(styleRefSlug,file.name,base64)}
const newPrimary=existingImages.find(img=>img.isPrimary&&!imagesToDelete.includes(img.path))
if(newPrimary&&originalStyleRef&&newPrimary.path!==originalStyleRef.primary_image){const filename=newPrimary.path.split('/').pop()||'';await setPrimaryStyleReferenceImage(styleRefSlug,filename)}
await refresh();toast.success(`Style Reference "${name.trim()}" updated`);onOpenChange(false)})
const handleReanalyze=async()=>{if(!styleRefSlug||isReanalyzing)return;setIsReanalyzing(true)
try{const analysis=await reanalyzeStyleReference(styleRefSlug);setOriginalStyleRef(prev=>prev?{...prev,analysis}:prev);toast.success('Style reference reanalyzed successfully')}catch(err){toast.error(err instanceof Error?err.message:'Failed to reanalyze style reference')}finally{setIsReanalyzing(false)}}
const handleClose=useCallback(()=>{if(!isSaving&&!isReanalyzing){onOpenChange(false);clearError();setUploadError(null)}},[isSaving,isReanalyzing,onOpenChange,clearError])
const hasChanges=originalStyleRef&&(name.trim()!==originalStyleRef.name||description.trim()!==originalStyleRef.description||defaultStrict!==originalStyleRef.default_strict||newImages.length>0||imagesToDelete.length>0||existingImages.some(img=>img.isPrimary&&img.path!==originalStyleRef.primary_image))
const visibleExistingImages=existingImages.filter(img=>!imagesToDelete.includes(img.path))
const isWorking=isLoading||isSaving||isReanalyzing
const error=loadError||saveError||uploadError
const loadingMsg=isLoading?'Loading style reference...':isReanalyzing?'Reanalyzing style reference...':'Saving changes...'
//Analysis summary - handles V1 and V2 with reanalyze button
const analysisSummary=originalStyleRef?.analysis?(
<div className="bg-muted/50 rounded-lg p-3 space-y-2">
<div className="flex items-center justify-between">
<span className="text-sm font-medium">Style Analysis</span>
<Button variant="outline" size="sm" onClick={handleReanalyze} disabled={isWorking} className="h-7 text-xs gap-1.5">
{isReanalyzing?<Loader2 className="h-3 w-3 animate-spin"/>:<RefreshCw className="h-3 w-3"/>}Reanalyze</Button>
</div>
<div className="text-xs text-muted-foreground space-y-1">
{isV2StyleReferenceAnalysis(originalStyleRef.analysis)?(<>
<div><span className="font-medium">Version:</span> V2 Semantic Analysis</div>
<div><span className="font-medium">Aspect Ratio:</span> {originalStyleRef.analysis.canvas.aspect_ratio}</div>
<div><span className="font-medium">Benefits:</span> {originalStyleRef.analysis.copywriting.benefits.length} identified</div>
{originalStyleRef.analysis.copywriting.benefits.length>0&&(
<div className="pl-2 border-l-2 border-muted text-muted-foreground/80 mt-1">{originalStyleRef.analysis.copywriting.benefits.slice(0,3).map((b,i)=><div key={i}>• {b}</div>)}{originalStyleRef.analysis.copywriting.benefits.length>3&&<div className="text-muted-foreground/60">...and {originalStyleRef.analysis.copywriting.benefits.length-3} more</div>}</div>)}
</>):(<>
<div><span className="font-medium">Version:</span> V1 Analysis</div>
<div><span className="font-medium">Aspect Ratio:</span> {originalStyleRef.analysis.canvas.aspect_ratio}</div>
<div><span className="font-medium">Elements:</span> {(originalStyleRef.analysis as any).elements?.length||0}</div>
<div><span className="font-medium">Product Slot:</span> {(originalStyleRef.analysis as any).product_slot?'Yes':'No'}</div>
</>)}
</div>
<p className="text-[10px] text-muted-foreground/60">Click Reanalyze to regenerate style analysis from images.</p>
</div>):null
return(<FormDialog open={open} onOpenChange={handleClose} title="Edit Style Reference" description="Update style reference details and images." icon={<Layout className="h-5 w-5"/>} iconColor="text-brand-500" isLoading={isWorking} loadingMessage={loadingMsg} error={error} onClearError={()=>{clearError();setUploadError(null)}} maxWidth="max-w-xl" footer={<>
<Button variant="outline" onClick={handleClose} disabled={isSaving}>Cancel</Button>
<Button onClick={()=>save()} disabled={isWorking||!name.trim()||!hasChanges} className="bg-brand-500 hover:bg-brand-600">{isSaving?'Saving...':'Save Changes'}</Button>
</>}>
{/*Name Input*/}
<div className="space-y-2">
<label htmlFor="edit-style-ref-name" className="text-sm font-medium">Name <span className="text-destructive">*</span></label>
<Input id="edit-style-ref-name" value={name} onChange={(e)=>setName(e.target.value)} placeholder="e.g., Hero Banner Style" autoFocus/>
</div>
{/*Description Input*/}
<div className="space-y-2">
<label htmlFor="edit-style-ref-description" className="text-sm font-medium">Description</label>
<textarea id="edit-style-ref-description" value={description} onChange={(e)=>setDescription(e.target.value)} placeholder="Describe the visual style and key elements" rows={4} className="w-full px-3 py-2 text-sm border rounded-md bg-transparent focus:outline-none focus:ring-2 focus:ring-brand-500 resize-y min-h-[80px]"/>
</div>
{/*Default Strict Toggle*/}
<div className="flex items-center justify-between py-2">
<div className="space-y-0.5">
<label htmlFor="edit-default-strict" className="text-sm font-medium">Strictly Follow by Default</label>
<p className="text-xs text-muted-foreground">When ON, new generations preserve exact style</p>
</div>
<button id="edit-default-strict" type="button" role="switch" aria-checked={defaultStrict} onClick={()=>setDefaultStrict(!defaultStrict)}
className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 ${defaultStrict?'bg-brand-500':'bg-neutral-200 dark:bg-neutral-700'}`}>
<span className={`pointer-events-none inline-block h-4 w-4 rounded-full bg-white shadow-lg ring-0 transition-transform ${defaultStrict?'translate-x-4':'translate-x-0'}`}/>
</button>
</div>
{/*Analysis Summary*/}
{analysisSummary}
{/*Reference Images*/}
<div className="space-y-2">
<label className="text-sm font-medium">Reference Images <span className="text-destructive">*</span> <span className="text-xs text-muted-foreground">(1-2 images)</span></label>
{/*Existing Images*/}
{visibleExistingImages.length>0&&(<div className="flex flex-wrap gap-2 mb-2">
{visibleExistingImages.map((img)=>(<div key={img.path} className={`relative group ${img.isPrimary?'ring-2 ring-brand-500 ring-offset-2':''}`}>
{img.thumbnailUrl?(<img src={img.thumbnailUrl} alt={img.filename} className="h-20 w-20 rounded object-cover border"/>
):(<div className="h-20 w-20 rounded border bg-neutral-100 dark:bg-neutral-800 flex items-center justify-center"><Loader2 className="h-4 w-4 text-neutral-400 animate-spin"/></div>)}
{img.isPrimary&&(<div className="absolute top-1 left-1 bg-brand-500 text-white rounded-full p-0.5"><Star className="h-3 w-3 fill-current"/></div>)}
<div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity rounded flex items-center justify-center gap-1">
{!img.isPrimary&&(<button type="button" onClick={()=>handleSetPrimary(img.path)} className="h-6 w-6 bg-brand-500 text-white rounded-full flex items-center justify-center hover:bg-brand-600" title="Set as primary"><Star className="h-3 w-3"/></button>)}
<button type="button" onClick={()=>handleDeleteExisting(img.path)} className="h-6 w-6 bg-destructive text-white rounded-full flex items-center justify-center hover:bg-destructive/90" title="Delete image"><X className="h-3 w-3"/></button>
</div>
<span className="absolute bottom-0 left-0 right-0 bg-black/60 text-white text-[10px] px-1 truncate rounded-b">{img.filename}</span>
</div>))}
</div>)}
{/*New Images*/}
{newImages.length>0&&(<div className="flex flex-wrap gap-2 mb-2">
{newImages.map((item,index)=>(<div key={index} className="relative group">
<img src={item.dataUrl} alt={item.file.name} className="h-20 w-20 rounded object-cover border border-dashed border-success"/>
<div className="absolute top-1 right-1 bg-success text-white text-[10px] px-1 rounded">NEW</div>
<button type="button" onClick={()=>handleDeleteNew(index)} className="absolute -top-1 -right-1 h-5 w-5 bg-destructive text-white rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"><X className="h-3 w-3"/></button>
<span className="absolute bottom-0 left-0 right-0 bg-black/60 text-white text-[10px] px-1 truncate rounded-b">{item.file.name}</span>
</div>))}
</div>)}
{/*Dropzone*/}
{(visibleExistingImages.length+newImages.length<2)&&(
<Dropzone accept={{'image/*':getAllowedImageExts().map(e=>e)}} maxFiles={2-visibleExistingImages.length-newImages.length} onDrop={handleFilesAdded} onError={handleDropError} className="border-dashed p-3">
<DropzoneEmptyState><div className="flex flex-col items-center"><p className="text-xs mb-1">Drop images to add</p></div></DropzoneEmptyState>
</Dropzone>)}
<p className="text-xs text-muted-foreground">Click the star to set the primary image.</p>
</div>
</FormDialog>)}
