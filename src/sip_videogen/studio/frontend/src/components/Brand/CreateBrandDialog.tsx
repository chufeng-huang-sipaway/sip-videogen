import{useState,useCallback}from'react'
import{Plus,X,FileText,Image}from'lucide-react'
import{Button}from'@/components/ui/button'
import{FormDialog}from'@/components/ui/form-dialog'
import{Dropzone,DropzoneEmptyState}from'@/components/ui/dropzone'
import{bridge,isPyWebView}from'@/lib/bridge'
import{getAllowedImageExts,getAllowedTextExts}from'@/lib/constants'
import{processUploadedFiles}from'@/lib/file-utils'
import type{ProcessedFile}from'@/lib/file-utils'
import{useAsyncAction}from'@/hooks/useAsyncAction'
import{toast}from'@/components/ui/toaster'
const MAX_DOC_SIZE=50*1024
interface CreateBrandDialogProps{open:boolean;onOpenChange:(open:boolean)=>void;onCreated:(slug:string)=>void}
export function CreateBrandDialog({open,onOpenChange,onCreated}:CreateBrandDialogProps){
const[description,setDescription]=useState('')
const[files,setFiles]=useState<ProcessedFile[]>([])
const[uploadError,setUploadError]=useState<string|null>(null)
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
const{execute,isLoading,error,clearError}=useAsyncAction(async()=>{
if(!description.trim()&&files.length===0)throw new Error('Please provide a description or upload files to describe your brand.')
const images:Array<{filename:string;data:string}>=[]
const documents:Array<{filename:string;data:string}>=[]
for(const{file,base64,type}of files){if(type==='image')images.push({filename:file.name,data:base64});else documents.push({filename:file.name,data:base64})}
if(isPyWebView()){const result=await bridge.createBrandFromMaterials(description,images,documents)
toast.success(`Brand "${result.name||result.slug}" created`);onCreated(result.slug);onOpenChange(false);setDescription('');setFiles([])}
})
const handleClose=useCallback(()=>{if(!isLoading){onOpenChange(false);setDescription('');setFiles([]);clearError();setUploadError(null)}},[isLoading,onOpenChange,clearError])
const combinedError=error||uploadError
return(<FormDialog open={open} onOpenChange={handleClose} title="Create New Brand" description="Upload brand materials and describe your vision. Our AI will create a complete brand identity." icon={<Plus className="h-5 w-5"/>} iconColor="text-purple-500" isLoading={isLoading} loadingMessage="Creating your brand identity... This may take a minute as our AI team analyzes your materials." error={combinedError} onClearError={()=>{clearError();setUploadError(null)}} maxWidth="max-w-lg" footer={<>
<Button variant="outline" onClick={handleClose} disabled={isLoading}>Cancel</Button>
<Button onClick={()=>execute()} disabled={isLoading||(!description.trim()&&files.length===0)} className="bg-purple-600 hover:bg-purple-700">{isLoading?'Creating...':'Create Brand'}</Button>
</>}>
{/* Dropzone */}
<Dropzone accept={{'image/*':getAllowedImageExts().map(e=>e),'text/*':getAllowedTextExts().map(e=>e)}} maxFiles={20} onDrop={handleFilesAdded} onError={handleDropError} className="border-dashed">
<DropzoneEmptyState><div className="flex flex-col items-center"><p className="text-sm font-medium mb-1">Drag & drop images or documents</p><p className="text-xs text-muted-foreground">PNG, JPG, SVG, MD, TXT</p></div></DropzoneEmptyState>
</Dropzone>
{/* File List */}
{files.length>0&&(<div className="flex flex-wrap gap-2">
{files.map((item,index)=>(<div key={index} className="flex items-center gap-2 px-2 py-1 bg-gray-100 dark:bg-gray-800 rounded text-sm">
{item.type==='image'?(item.dataUrl?(<img src={item.dataUrl} alt="" className="h-5 w-5 rounded object-cover"/>):(<Image className="h-4 w-4 text-gray-500"/>)):(<FileText className="h-4 w-4 text-gray-500"/>)}
<span className="max-w-[120px] truncate">{item.file.name}</span>
<button type="button" onClick={()=>removeFile(index)} className="text-gray-400 hover:text-gray-600"><X className="h-4 w-4"/></button>
</div>))}
</div>)}
{/* Description */}
<div>
<textarea value={description} onChange={(e)=>setDescription(e.target.value)} placeholder="Tell us about your brand... (describe your concept, target audience, values, style preferences)" rows={4} className="w-full px-3 py-2 text-sm border rounded-md bg-transparent focus:outline-none focus:ring-2 focus:ring-purple-500 resize-none"/>
</div>
</FormDialog>)}
