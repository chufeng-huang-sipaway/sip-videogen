import{useState,useCallback}from'react'
import{Package,X}from'lucide-react'
import{Button}from'@/components/ui/button'
import{FormDialog}from'@/components/ui/form-dialog'
import{Input}from'@/components/ui/input'
import{Dropzone,DropzoneEmptyState}from'@/components/ui/dropzone'
import{useProducts}from'@/context/ProductContext'
import{useAsyncAction}from'@/hooks/useAsyncAction'
import{processImageFiles}from'@/lib/file-utils'
import type{ProcessedFile}from'@/lib/file-utils'
import{getAllowedImageExts}from'@/lib/constants'
import{toast}from'@/components/ui/toaster'
interface CreateProductDialogProps{open:boolean;onOpenChange:(open:boolean)=>void;onCreated?:(slug:string)=>void}
export function CreateProductDialog({open,onOpenChange,onCreated}:CreateProductDialogProps){
const{createProduct,refresh}=useProducts()
const[name,setName]=useState('')
const[description,setDescription]=useState('')
const[images,setImages]=useState<ProcessedFile[]>([])
const[uploadError,setUploadError]=useState<string|null>(null)
const handleFilesAdded=useCallback(async(files:File[])=>{
setUploadError(null)
const{processed,rejected}=await processImageFiles(files)
if(rejected.length>0)setUploadError(`Unsupported files: ${rejected.join(', ')}`)
setImages(prev=>[...prev,...processed])
},[])
const handleDropError=useCallback((err:Error)=>{setUploadError(err.message||'Failed to add files.')},[])
const removeImage=(index:number)=>setImages(prev=>prev.filter((_,i)=>i!==index))
const{execute,isLoading,error,clearError}=useAsyncAction(async()=>{
if(!name.trim())throw new Error('Please enter a product name.')
const imageData=images.map(({file,base64})=>({filename:file.name,data:base64}))
const slug=await createProduct({name:name.trim(),description:description.trim(),images:imageData.length>0?imageData:undefined})
await refresh();toast.success(`Product "${name.trim()}" created`);onCreated?.(slug);onOpenChange(false)
setName('');setDescription('');setImages([])
})
const handleClose=useCallback(()=>{if(!isLoading){onOpenChange(false);setName('');setDescription('');setImages([]);clearError();setUploadError(null)}},[isLoading,onOpenChange,clearError])
const combinedError=error||uploadError
return(<FormDialog open={open} onOpenChange={handleClose} title="Add New Product" description="Add a product with reference images for AI-powered generation." icon={<Package className="h-5 w-5"/>} iconColor="text-brand-500" isLoading={isLoading} loadingMessage="Creating product..." error={combinedError} onClearError={()=>{clearError();setUploadError(null)}} footer={<>
<Button variant="outline" onClick={handleClose} disabled={isLoading}>Cancel</Button>
<Button onClick={()=>execute()} disabled={isLoading||!name.trim()}>{isLoading?'Creating...':'Add Product'}</Button>
</>}>
{/* Name Input */}
<div className="space-y-2">
<label htmlFor="product-name" className="text-sm font-medium">Name <span className="text-destructive">*</span></label>
<Input id="product-name" value={name} onChange={(e)=>setName(e.target.value)} placeholder="e.g., Night Cream 50ml" autoFocus/>
</div>
{/* Description Input */}
<div className="space-y-2">
<label htmlFor="product-description" className="text-sm font-medium">Description</label>
<textarea id="product-description" value={description} onChange={(e)=>setDescription(e.target.value)} placeholder="Describe the product (size, texture, use cases, etc.)" rows={3} className="w-full px-3 py-2 text-sm border rounded-md bg-transparent focus:outline-none focus:ring-2 focus:ring-ring resize-none"/>
</div>
{/* Image Dropzone */}
<div className="space-y-2">
<label className="text-sm font-medium">Product Images</label>
<Dropzone accept={{'image/*':getAllowedImageExts().map(e=>e)}} maxFiles={20} onDrop={handleFilesAdded} onError={handleDropError} className="border-dashed">
<DropzoneEmptyState><div className="flex flex-col items-center"><p className="text-sm mb-1">Drag & drop product images</p><p className="text-xs text-muted-foreground">PNG, JPG, GIF, WebP</p></div></DropzoneEmptyState>
</Dropzone>
</div>
{/* Image Preview List */}
{images.length>0&&(<div className="flex flex-wrap gap-2">
{images.map((item,index)=>(<div key={index} className="relative group">
<img src={item.dataUrl} alt={item.file.name} className="h-16 w-16 rounded object-cover border"/>
<button type="button" onClick={()=>removeImage(index)} className="absolute -top-1 -right-1 h-5 w-5 bg-destructive text-white rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"><X className="h-3 w-3"/></button>
<span className="absolute bottom-0 left-0 right-0 bg-black/60 text-white text-[10px] px-1 truncate rounded-b">{item.file.name}</span>
</div>))}
</div>)}
{images.length===0&&(<p className="text-xs text-muted-foreground">Tip: Upload product photos so the AI can use them as reference when generating images.</p>)}
</FormDialog>)}
