import{useState,useCallback}from'react'
import{Plus,X,FileText,Image,Globe}from'lucide-react'
import{Button}from'@/components/ui/button'
import{FormDialog}from'@/components/ui/form-dialog'
import{Dropzone,DropzoneEmptyState}from'@/components/ui/dropzone'
import{Tabs,TabsList,TabsTrigger,TabsContent}from'@/components/ui/tabs'
import{bridge,isPyWebView}from'@/lib/bridge'
import{getAllowedImageExts,getAllowedTextExts}from'@/lib/constants'
import{processUploadedFiles}from'@/lib/file-utils'
import type{ProcessedFile}from'@/lib/file-utils'
import{useAsyncAction}from'@/hooks/useAsyncAction'
import{toast}from'@/components/ui/toaster'
import{useBrand}from'@/context/BrandContext'
const MAX_DOC_SIZE=50*1024
type CreateMode='materials'|'website'
interface CreateBrandDialogProps{open:boolean;onOpenChange:(open:boolean)=>void;onCreated:(slug:string)=>void;hasActiveJob?:boolean}
export function CreateBrandDialog({open,onOpenChange,onCreated,hasActiveJob}:CreateBrandDialogProps){
const{startBrandCreation}=useBrand()
const[mode,setMode]=useState<CreateMode>('materials')
const[description,setDescription]=useState('')
const[files,setFiles]=useState<ProcessedFile[]>([])
const[uploadError,setUploadError]=useState<string|null>(null)
//Website mode state
const[brandName,setBrandName]=useState('')
const[websiteUrl,setWebsiteUrl]=useState('')
const handleFilesAdded=useCallback(async(newFiles:File[])=>{
setUploadError(null)
const allExts=[...getAllowedImageExts(),...getAllowedTextExts()]
const{processed,rejected}=await processUploadedFiles(newFiles,allExts)
//Check doc size
const validFiles:ProcessedFile[]=[]
for(const f of processed){if(f.type==='document'&&f.file.size>MAX_DOC_SIZE){setUploadError(`"${f.file.name}" is too large (max 50KB).`);continue}validFiles.push(f)}
if(rejected.length>0)setUploadError(`Unsupported files: ${rejected.join(', ')}`)
setFiles(prev=>[...prev,...validFiles])
},[])
const handleDropError=useCallback((err:Error)=>{setUploadError(err.message||'Failed to add files.')},[])
const removeFile=(index:number)=>setFiles(prev=>prev.filter((_,i)=>i!==index))
//Materials mode action
const{execute:execMaterials,isLoading:isMaterialsLoading,error:materialsError,clearError:clearMaterialsError}=useAsyncAction(async()=>{
if(!description.trim()&&files.length===0)throw new Error('Please provide a description or upload files to describe your brand.')
const images:Array<{filename:string;data:string}>=[]
const documents:Array<{filename:string;data:string}>=[]
for(const{file,base64,type}of files){if(type==='image')images.push({filename:file.name,data:base64});else documents.push({filename:file.name,data:base64})}
if(isPyWebView()){const result=await bridge.createBrandFromMaterials(description,images,documents)
toast.success(`Brand "${result.name||result.slug}" created`);onCreated(result.slug);onOpenChange(false);resetState()}
})
//Website mode action - uses context to trigger polling
const{execute:execWebsite,isLoading:isWebsiteLoading,error:websiteError,clearError:clearWebsiteError}=useAsyncAction(async()=>{
const n=brandName.trim()
const u=websiteUrl.trim()
if(!n)throw new Error('Please enter a brand name.')
if(!u)throw new Error('Please enter a website URL.')
//Basic URL validation
const urlPattern=/^(https?:\/\/)?([a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}/
if(!urlPattern.test(u))throw new Error('Please enter a valid website URL (e.g., example.com)')
if(isPyWebView()){await startBrandCreation(n,u)//Context handles polling & completion
toast.success(`Creating brand "${n}"... This may take a few minutes.`);onOpenChange(false);resetState()}
})
const resetState=()=>{setDescription('');setFiles([]);setBrandName('');setWebsiteUrl('');setMode('materials')}
const handleClose=useCallback(()=>{const isLoading=isMaterialsLoading||isWebsiteLoading
if(!isLoading){onOpenChange(false);resetState();clearMaterialsError();clearWebsiteError();setUploadError(null)}},[isMaterialsLoading,isWebsiteLoading,onOpenChange,clearMaterialsError,clearWebsiteError])
const isLoading=isMaterialsLoading||isWebsiteLoading
const combinedError=mode==='materials'?(materialsError||uploadError):websiteError
const canSubmitMaterials=description.trim()||files.length>0
const canSubmitWebsite=brandName.trim()&&websiteUrl.trim()&&!hasActiveJob
return(<FormDialog open={open} onOpenChange={handleClose} title="Create New Brand" description="Create a brand identity using materials or just a website URL." icon={<Plus className="h-5 w-5"/>} iconColor="text-brand-500" isLoading={isLoading} loadingMessage={mode==='materials'?"Creating your brand identity... This may take a minute as our AI team analyzes your materials.":"Starting brand research... This runs in the background and may take a few minutes."} error={combinedError} onClearError={()=>{clearMaterialsError();clearWebsiteError();setUploadError(null)}} maxWidth="max-w-lg" footer={<>
<Button variant="outline" onClick={handleClose} disabled={isLoading}>Cancel</Button>
{mode==='materials'?(<Button onClick={()=>execMaterials()} disabled={isLoading||!canSubmitMaterials}>{isLoading?'Creating...':'Create Brand'}</Button>):(<Button onClick={()=>execWebsite()} disabled={isLoading||!canSubmitWebsite}>{isLoading?'Starting...':'Create Brand'}</Button>)}
</>}>
{/* Mode Toggle */}
<Tabs value={mode} onValueChange={(v)=>setMode(v as CreateMode)} className="w-full">
<TabsList className="w-full">
<TabsTrigger value="materials" className="flex-1 gap-1.5"><FileText className="h-4 w-4"/>Upload Materials</TabsTrigger>
<TabsTrigger value="website" className="flex-1 gap-1.5" disabled={hasActiveJob}><Globe className="h-4 w-4"/>From Website</TabsTrigger>
</TabsList>
<TabsContent value="materials" className="space-y-4 mt-4">
{/* Dropzone */}
<Dropzone accept={{'image/*':getAllowedImageExts().map(e=>e),'text/*':getAllowedTextExts().map(e=>e)}} maxFiles={20} onDrop={handleFilesAdded} onError={handleDropError} className="border-dashed">
<DropzoneEmptyState><div className="flex flex-col items-center"><p className="text-sm font-medium mb-1">Drag & drop images or documents</p><p className="text-xs text-muted-foreground">PNG, JPG, SVG, MD, TXT</p></div></DropzoneEmptyState>
</Dropzone>
{/* File List */}
{files.length>0&&(<div className="flex flex-wrap gap-2">
{files.map((item,index)=>(<div key={index} className="flex items-center gap-2 px-2 py-1 bg-neutral-100 dark:bg-neutral-800 rounded text-sm">
{item.type==='image'?(item.dataUrl?(<img src={item.dataUrl} alt="" className="h-5 w-5 rounded object-cover"/>):(<Image className="h-4 w-4 text-muted-foreground"/>)):(<FileText className="h-4 w-4 text-muted-foreground"/>)}
<span className="max-w-[120px] truncate">{item.file.name}</span>
<button type="button" onClick={()=>removeFile(index)} className="text-muted-foreground hover:text-foreground"><X className="h-4 w-4"/></button>
</div>))}
</div>)}
{/* Description */}
<div>
<textarea value={description} onChange={(e)=>setDescription(e.target.value)} placeholder="Tell us about your brand... (describe your concept, target audience, values, style preferences)" rows={4} className="w-full px-3 py-2 text-sm border rounded-md bg-transparent focus:outline-none focus:ring-2 focus:ring-ring resize-none"/>
</div>
</TabsContent>
<TabsContent value="website" className="space-y-4 mt-4">
{hasActiveJob?(<div className="p-4 rounded-md bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800"><p className="text-sm text-amber-800 dark:text-amber-200">Brand creation is already in progress. Please wait for it to complete.</p></div>):(<>
{/* Brand Name */}
<div>
<label htmlFor="brand-name" className="block text-sm font-medium mb-1.5">Brand Name</label>
<input id="brand-name" type="text" value={brandName} onChange={(e)=>setBrandName(e.target.value)} placeholder="e.g., Acme Corporation" className="w-full px-3 py-2 text-sm border rounded-md bg-transparent focus:outline-none focus:ring-2 focus:ring-ring"/>
</div>
{/* Website URL */}
<div>
<label htmlFor="website-url" className="block text-sm font-medium mb-1.5">Website URL</label>
<input id="website-url" type="text" value={websiteUrl} onChange={(e)=>setWebsiteUrl(e.target.value)} placeholder="e.g., acme.com or https://acme.com" className="w-full px-3 py-2 text-sm border rounded-md bg-transparent focus:outline-none focus:ring-2 focus:ring-ring"/>
<p className="mt-1.5 text-xs text-muted-foreground">We'll analyze the website to understand your brand's visual identity and messaging.</p>
</div>
</>)}
</TabsContent>
</Tabs>
</FormDialog>)}
