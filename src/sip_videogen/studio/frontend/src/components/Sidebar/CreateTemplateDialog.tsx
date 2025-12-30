//CreateTemplateDialog for creating new layout templates
import{useState,useCallback}from'react'
import{Layout,X}from'lucide-react'
import{Button}from'@/components/ui/button'
import{FormDialog}from'@/components/ui/form-dialog'
import{Input}from'@/components/ui/input'
import{Dropzone,DropzoneEmptyState}from'@/components/ui/dropzone'
import{useTemplates}from'@/context/TemplateContext'
import{useAsyncAction}from'@/hooks/useAsyncAction'
import{processImageFiles}from'@/lib/file-utils'
import type{ProcessedFile}from'@/lib/file-utils'
import{getAllowedImageExts}from'@/lib/constants'
import{toast}from'@/components/ui/toaster'
interface CreateTemplateDialogProps{open:boolean;onOpenChange:(open:boolean)=>void;onCreated?:(slug:string)=>void}
export function CreateTemplateDialog({open,onOpenChange,onCreated}:CreateTemplateDialogProps){
const{createTemplate,refresh}=useTemplates()
const[name,setName]=useState('')
const[description,setDescription]=useState('')
const[defaultStrict,setDefaultStrict]=useState(true)
const[images,setImages]=useState<ProcessedFile[]>([])
const[uploadError,setUploadError]=useState<string|null>(null)
const handleFilesAdded=useCallback(async(files:File[])=>{
setUploadError(null)
const{processed,rejected}=await processImageFiles(files)
if(rejected.length>0)setUploadError(`Unsupported files: ${rejected.join(', ')}`)
//Limit to 2 images max for templates
const remaining=2-images.length
if(processed.length>remaining){
setUploadError(prev=>prev?prev+' Templates allow max 2 images.':'Templates allow max 2 images.')
setImages(prev=>[...prev,...processed.slice(0,remaining)])}
else setImages(prev=>[...prev,...processed])},[images.length])
const handleDropError=useCallback((err:Error)=>{setUploadError(err.message||'Failed to add files.')},[])
const removeImage=(index:number)=>setImages(prev=>prev.filter((_,i)=>i!==index))
const{execute,isLoading,error,clearError}=useAsyncAction(async()=>{
if(!name.trim())throw new Error('Please enter a template name.')
if(images.length===0)throw new Error('Please add at least one template image.')
const imageData=images.map(({file,base64})=>({filename:file.name,data:base64}))
const slug=await createTemplate({name:name.trim(),description:description.trim(),images:imageData,defaultStrict})
await refresh();toast.success(`Template "${name.trim()}" created`);onCreated?.(slug);onOpenChange(false)
setName('');setDescription('');setDefaultStrict(true);setImages([])})
const handleClose=useCallback(()=>{if(!isLoading){onOpenChange(false);setName('');setDescription('');setDefaultStrict(true);setImages([]);clearError();setUploadError(null)}},[isLoading,onOpenChange,clearError])
const combinedError=error||uploadError
return(<FormDialog open={open} onOpenChange={handleClose} title="Add New Template" description="Create a layout template from reference images. AI will analyze the composition." icon={<Layout className="h-5 w-5"/>} iconColor="text-brand-500" isLoading={isLoading} loadingMessage="Creating template..." error={combinedError} onClearError={()=>{clearError();setUploadError(null)}} footer={<>
<Button variant="outline" onClick={handleClose} disabled={isLoading}>Cancel</Button>
<Button onClick={()=>execute()} disabled={isLoading||!name.trim()||images.length===0} className="bg-brand-500 hover:bg-brand-600">{isLoading?'Creating...':'Add Template'}</Button>
</>}>
{/*Name Input*/}
<div className="space-y-2">
<label htmlFor="template-name" className="text-sm font-medium">Name <span className="text-destructive">*</span></label>
<Input id="template-name" value={name} onChange={(e)=>setName(e.target.value)} placeholder="e.g., Hero Banner Layout" autoFocus/>
</div>
{/*Description Input*/}
<div className="space-y-2">
<label htmlFor="template-description" className="text-sm font-medium">Description</label>
<textarea id="template-description" value={description} onChange={(e)=>setDescription(e.target.value)} placeholder="Describe the layout purpose (e.g., product hero, promotional banner, social post)" rows={2} className="w-full px-3 py-2 text-sm border rounded-md bg-transparent focus:outline-none focus:ring-2 focus:ring-brand-500 resize-none"/>
</div>
{/*Default Strict Toggle*/}
<div className="flex items-center justify-between py-2">
<div className="space-y-0.5">
<label htmlFor="default-strict" className="text-sm font-medium">Strictly Follow by Default</label>
<p className="text-xs text-muted-foreground">When ON, new generations preserve exact layout</p>
</div>
<button id="default-strict" type="button" role="switch" aria-checked={defaultStrict} onClick={()=>setDefaultStrict(!defaultStrict)}
className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 ${defaultStrict?'bg-brand-500':'bg-neutral-200 dark:bg-neutral-700'}`}>
<span className={`pointer-events-none inline-block h-4 w-4 rounded-full bg-white shadow-lg ring-0 transition-transform ${defaultStrict?'translate-x-4':'translate-x-0'}`}/>
</button>
</div>
{/*Image Dropzone*/}
<div className="space-y-2">
<label className="text-sm font-medium">Template Images <span className="text-destructive">*</span> <span className="text-xs text-muted-foreground">(1-2 images)</span></label>
<Dropzone accept={{'image/*':getAllowedImageExts().map(e=>e)}} maxFiles={2} onDrop={handleFilesAdded} onError={handleDropError} className="border-dashed">
<DropzoneEmptyState><div className="flex flex-col items-center"><p className="text-sm mb-1">Drag & drop layout images</p><p className="text-xs text-muted-foreground">PNG, JPG, GIF, WebP</p></div></DropzoneEmptyState>
</Dropzone>
</div>
{/*Image Preview List*/}
{images.length>0&&(<div className="flex flex-wrap gap-2">
{images.map((item,index)=>(<div key={index} className="relative group">
<img src={item.dataUrl} alt={item.file.name} className="h-20 w-20 rounded object-cover border"/>
<button type="button" onClick={()=>removeImage(index)} className="absolute -top-1 -right-1 h-5 w-5 bg-destructive text-white rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"><X className="h-3 w-3"/></button>
<span className="absolute bottom-0 left-0 right-0 bg-black/60 text-white text-[10px] px-1 truncate rounded-b">{item.file.name}</span>
</div>))}
</div>)}
{images.length===0&&(<p className="text-xs text-muted-foreground">Upload 1-2 reference images showing the desired layout composition.</p>)}
</FormDialog>)}
