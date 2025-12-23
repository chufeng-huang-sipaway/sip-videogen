//EditTemplateDialog for editing existing layout templates
import{useState,useEffect,useCallback}from'react'
import{Layout,X,Star,Loader2}from'lucide-react'
import{Button}from'@/components/ui/button'
import{FormDialog}from'@/components/ui/form-dialog'
import{Input}from'@/components/ui/input'
import{Dropzone,DropzoneEmptyState}from'@/components/ui/dropzone'
import{useTemplates}from'@/context/TemplateContext'
import{useAsyncAction}from'@/hooks/useAsyncAction'
import{processImageFiles}from'@/lib/file-utils'
import type{ProcessedFile}from'@/lib/file-utils'
import{bridge,isPyWebView}from'@/lib/bridge'
import{ALLOWED_IMAGE_EXTS}from'@/lib/constants'
import{toast}from'@/components/ui/toaster'
import type{TemplateFull}from'@/lib/bridge'
interface ExistingImage{path:string;filename:string;thumbnailUrl:string|null;isPrimary:boolean}
interface EditTemplateDialogProps{open:boolean;onOpenChange:(open:boolean)=>void;templateSlug:string}
export function EditTemplateDialog({open,onOpenChange,templateSlug}:EditTemplateDialogProps){
const{getTemplate,getTemplateImages,updateTemplate,uploadTemplateImage,deleteTemplateImage,setPrimaryTemplateImage,refresh}=useTemplates()
const[name,setName]=useState('')
const[description,setDescription]=useState('')
const[defaultStrict,setDefaultStrict]=useState(true)
const[existingImages,setExistingImages]=useState<ExistingImage[]>([])
const[newImages,setNewImages]=useState<ProcessedFile[]>([])
const[imagesToDelete,setImagesToDelete]=useState<string[]>([])
const[isLoading,setIsLoading]=useState(true)
const[loadError,setLoadError]=useState<string|null>(null)
const[originalTemplate,setOriginalTemplate]=useState<TemplateFull|null>(null)
const[uploadError,setUploadError]=useState<string|null>(null)
//Load template data when dialog opens
useEffect(()=>{if(!open||!templateSlug)return
let cancelled=false
async function load(){setIsLoading(true);setLoadError(null);setNewImages([]);setImagesToDelete([])
try{const[template,imagePaths]=await Promise.all([getTemplate(templateSlug),getTemplateImages(templateSlug)])
if(cancelled)return
setOriginalTemplate(template);setName(template.name);setDescription(template.description);setDefaultStrict(template.default_strict)
const images:ExistingImage[]=[]
for(const path of imagePaths){const filename=path.split('/').pop()||path
let thumbnailUrl:string|null=null
if(isPyWebView()){try{thumbnailUrl=await bridge.getTemplateImageThumbnail(path)}catch{}}
images.push({path,filename,thumbnailUrl,isPrimary:path===template.primary_image})}
if(!cancelled){images.sort((a,b)=>(b.isPrimary?1:0)-(a.isPrimary?1:0));setExistingImages(images)}
}catch(err){if(!cancelled)setLoadError(err instanceof Error?err.message:'Failed to load template')
}finally{if(!cancelled)setIsLoading(false)}}
load();return()=>{cancelled=true}},[open,templateSlug,getTemplate,getTemplateImages])
const handleFilesAdded=useCallback(async(files:File[])=>{
setUploadError(null)
const{processed,rejected}=await processImageFiles(files)
if(rejected.length>0)setUploadError(`Unsupported files: ${rejected.join(', ')}`)
//Limit to 2 images max total
const totalExisting=existingImages.filter(img=>!imagesToDelete.includes(img.path)).length
const totalNew=newImages.length
const remaining=2-totalExisting-totalNew
if(remaining<=0){setUploadError('Templates allow max 2 images.');return}
if(processed.length>remaining){
setUploadError(prev=>prev?prev+' Max 2 images.':'Max 2 images.')
setNewImages(prev=>[...prev,...processed.slice(0,remaining)])}
else setNewImages(prev=>[...prev,...processed])},[existingImages,imagesToDelete,newImages.length])
const handleDropError=useCallback((err:Error)=>{setUploadError(err.message||'Failed to add files.')},[])
const handleDeleteExisting=(path:string)=>{setImagesToDelete(prev=>[...prev,path]);setExistingImages(prev=>prev.filter(img=>img.path!==path))}
const handleDeleteNew=(index:number)=>setNewImages(prev=>prev.filter((_,i)=>i!==index))
const handleSetPrimary=(path:string)=>{setExistingImages(prev=>prev.map(img=>({...img,isPrimary:img.path===path})).sort((a,b)=>(b.isPrimary?1:0)-(a.isPrimary?1:0)))}
const{execute:save,isLoading:isSaving,error:saveError,clearError}=useAsyncAction(async()=>{
if(!name.trim())throw new Error('Please enter a template name.')
const remainingExisting=existingImages.filter(img=>!imagesToDelete.includes(img.path))
if(remainingExisting.length===0&&newImages.length===0)throw new Error('Template must have at least one image.')
if(remainingExisting.length+newImages.length>2)throw new Error('Templates allow max 2 images.')
await updateTemplate(templateSlug,name.trim(),description.trim(),defaultStrict)
for(const path of imagesToDelete){const filename=path.split('/').pop()||'';await deleteTemplateImage(templateSlug,filename)}
for(const{file,base64}of newImages){await uploadTemplateImage(templateSlug,file.name,base64)}
const newPrimary=existingImages.find(img=>img.isPrimary&&!imagesToDelete.includes(img.path))
if(newPrimary&&originalTemplate&&newPrimary.path!==originalTemplate.primary_image){const filename=newPrimary.path.split('/').pop()||'';await setPrimaryTemplateImage(templateSlug,filename)}
await refresh();toast.success(`Template "${name.trim()}" updated`);onOpenChange(false)})
const handleClose=useCallback(()=>{if(!isSaving){onOpenChange(false);clearError();setUploadError(null)}},[isSaving,onOpenChange,clearError])
const hasChanges=originalTemplate&&(name.trim()!==originalTemplate.name||description.trim()!==originalTemplate.description||defaultStrict!==originalTemplate.default_strict||newImages.length>0||imagesToDelete.length>0||existingImages.some(img=>img.isPrimary&&img.path!==originalTemplate.primary_image))
const visibleExistingImages=existingImages.filter(img=>!imagesToDelete.includes(img.path))
const isWorking=isLoading||isSaving
const error=loadError||saveError||uploadError
const loadingMsg=isLoading?'Loading template...':'Saving changes...'
//Analysis summary
const analysisSummary=originalTemplate?.analysis?(
<div className="text-xs text-muted-foreground bg-muted/50 rounded p-2 space-y-1">
<span className="font-medium">Analysis:</span>{' '}
<span>{originalTemplate.analysis.elements.length} elements, </span>
<span>{originalTemplate.analysis.canvas.aspect_ratio} aspect, </span>
<span>{originalTemplate.analysis.product_slot?'has product slot':'no product slot'}</span>
</div>):null
return(<FormDialog open={open} onOpenChange={handleClose} title="Edit Template" description="Update template details and images." icon={<Layout className="h-5 w-5"/>} iconColor="text-indigo-500" isLoading={isWorking} loadingMessage={loadingMsg} error={error} onClearError={()=>{clearError();setUploadError(null)}} maxWidth="max-w-lg" footer={<>
<Button variant="outline" onClick={handleClose} disabled={isSaving}>Cancel</Button>
<Button onClick={()=>save()} disabled={isWorking||!name.trim()||!hasChanges} className="bg-indigo-600 hover:bg-indigo-700">{isSaving?'Saving...':'Save Changes'}</Button>
</>}>
{/*Name Input*/}
<div className="space-y-2">
<label htmlFor="edit-template-name" className="text-sm font-medium">Name <span className="text-red-500">*</span></label>
<Input id="edit-template-name" value={name} onChange={(e)=>setName(e.target.value)} placeholder="e.g., Hero Banner Layout" autoFocus/>
</div>
{/*Description Input*/}
<div className="space-y-2">
<label htmlFor="edit-template-description" className="text-sm font-medium">Description</label>
<textarea id="edit-template-description" value={description} onChange={(e)=>setDescription(e.target.value)} placeholder="Describe the layout purpose" rows={2} className="w-full px-3 py-2 text-sm border rounded-md bg-transparent focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none"/>
</div>
{/*Default Strict Toggle*/}
<div className="flex items-center justify-between py-2">
<div className="space-y-0.5">
<label htmlFor="edit-default-strict" className="text-sm font-medium">Strictly Follow by Default</label>
<p className="text-xs text-muted-foreground">When ON, new generations preserve exact layout</p>
</div>
<button id="edit-default-strict" type="button" role="switch" aria-checked={defaultStrict} onClick={()=>setDefaultStrict(!defaultStrict)}
className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 ${defaultStrict?'bg-indigo-600':'bg-gray-200 dark:bg-gray-700'}`}>
<span className={`pointer-events-none inline-block h-4 w-4 rounded-full bg-white shadow-lg ring-0 transition-transform ${defaultStrict?'translate-x-4':'translate-x-0'}`}/>
</button>
</div>
{/*Analysis Summary*/}
{analysisSummary}
{/*Template Images*/}
<div className="space-y-2">
<label className="text-sm font-medium">Template Images <span className="text-red-500">*</span> <span className="text-xs text-muted-foreground">(1-2 images)</span></label>
{/*Existing Images*/}
{visibleExistingImages.length>0&&(<div className="flex flex-wrap gap-2 mb-2">
{visibleExistingImages.map((img)=>(<div key={img.path} className={`relative group ${img.isPrimary?'ring-2 ring-indigo-500 ring-offset-2':''}`}>
{img.thumbnailUrl?(<img src={img.thumbnailUrl} alt={img.filename} className="h-20 w-20 rounded object-cover border"/>
):(<div className="h-20 w-20 rounded border bg-gray-100 dark:bg-gray-800 flex items-center justify-center"><Loader2 className="h-4 w-4 text-gray-400 animate-spin"/></div>)}
{img.isPrimary&&(<div className="absolute top-1 left-1 bg-indigo-500 text-white rounded-full p-0.5"><Star className="h-3 w-3 fill-current"/></div>)}
<div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity rounded flex items-center justify-center gap-1">
{!img.isPrimary&&(<button type="button" onClick={()=>handleSetPrimary(img.path)} className="h-6 w-6 bg-indigo-500 text-white rounded-full flex items-center justify-center hover:bg-indigo-600" title="Set as primary"><Star className="h-3 w-3"/></button>)}
<button type="button" onClick={()=>handleDeleteExisting(img.path)} className="h-6 w-6 bg-red-500 text-white rounded-full flex items-center justify-center hover:bg-red-600" title="Delete image"><X className="h-3 w-3"/></button>
</div>
<span className="absolute bottom-0 left-0 right-0 bg-black/60 text-white text-[10px] px-1 truncate rounded-b">{img.filename}</span>
</div>))}
</div>)}
{/*New Images*/}
{newImages.length>0&&(<div className="flex flex-wrap gap-2 mb-2">
{newImages.map((item,index)=>(<div key={index} className="relative group">
<img src={item.dataUrl} alt={item.file.name} className="h-20 w-20 rounded object-cover border border-dashed border-green-500"/>
<div className="absolute top-1 right-1 bg-green-500 text-white text-[10px] px-1 rounded">NEW</div>
<button type="button" onClick={()=>handleDeleteNew(index)} className="absolute -top-1 -right-1 h-5 w-5 bg-red-500 text-white rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"><X className="h-3 w-3"/></button>
<span className="absolute bottom-0 left-0 right-0 bg-black/60 text-white text-[10px] px-1 truncate rounded-b">{item.file.name}</span>
</div>))}
</div>)}
{/*Dropzone*/}
{(visibleExistingImages.length+newImages.length<2)&&(
<Dropzone accept={{'image/*':ALLOWED_IMAGE_EXTS.map(e=>e)}} maxFiles={2-visibleExistingImages.length-newImages.length} onDrop={handleFilesAdded} onError={handleDropError} className="border-dashed p-3">
<DropzoneEmptyState><div className="flex flex-col items-center"><p className="text-xs mb-1">Drop images to add</p></div></DropzoneEmptyState>
</Dropzone>)}
<p className="text-xs text-muted-foreground">Click the star to set the primary image.</p>
</div>
</FormDialog>)}
