import{useState,useEffect,useCallback}from'react'
import{Package,X,Star,Loader2}from'lucide-react'
import{Button}from'@/components/ui/button'
import{FormDialog}from'@/components/ui/form-dialog'
import{Input}from'@/components/ui/input'
import{Dropzone,DropzoneEmptyState}from'@/components/ui/dropzone'
import{useProducts}from'@/context/ProductContext'
import{useAsyncAction}from'@/hooks/useAsyncAction'
import{processImageFiles}from'@/lib/file-utils'
import type{ProcessedFile}from'@/lib/file-utils'
import{bridge,isPyWebView}from'@/lib/bridge'
import{getAllowedImageExts}from'@/lib/constants'
import{toast}from'@/components/ui/toaster'
import type{ProductFull}from'@/lib/bridge'
interface ExistingImage{path:string;filename:string;thumbnailUrl:string|null;isPrimary:boolean}
interface EditProductDialogProps{open:boolean;onOpenChange:(open:boolean)=>void;productSlug:string}
export function EditProductDialog({open,onOpenChange,productSlug}:EditProductDialogProps){
const{getProduct,getProductImages,updateProduct,uploadProductImage,deleteProductImage,setPrimaryProductImage,refresh}=useProducts()
const[name,setName]=useState('')
const[description,setDescription]=useState('')
const[existingImages,setExistingImages]=useState<ExistingImage[]>([])
const[newImages,setNewImages]=useState<ProcessedFile[]>([])
const[imagesToDelete,setImagesToDelete]=useState<string[]>([])
const[isLoading,setIsLoading]=useState(true)
const[loadError,setLoadError]=useState<string|null>(null)
const[originalProduct,setOriginalProduct]=useState<ProductFull|null>(null)
const[uploadError,setUploadError]=useState<string|null>(null)
//Load product data when dialog opens
useEffect(()=>{if(!open||!productSlug)return
let cancelled=false
async function load(){setIsLoading(true);setLoadError(null);setNewImages([]);setImagesToDelete([])
try{const[product,imagePaths]=await Promise.all([getProduct(productSlug),getProductImages(productSlug)])
if(cancelled)return
setOriginalProduct(product);setName(product.name);setDescription(product.description)
const images:ExistingImage[]=[]
for(const path of imagePaths){const filename=path.split('/').pop()||path
let thumbnailUrl:string|null=null
if(isPyWebView()){try{thumbnailUrl=await bridge.getProductImageThumbnail(path)}catch{}}
images.push({path,filename,thumbnailUrl,isPrimary:path===product.primary_image})}
if(!cancelled){images.sort((a,b)=>(b.isPrimary?1:0)-(a.isPrimary?1:0));setExistingImages(images)}
}catch(err){if(!cancelled)setLoadError(err instanceof Error?err.message:'Failed to load product')
}finally{if(!cancelled)setIsLoading(false)}}
load();return()=>{cancelled=true}},[open,productSlug,getProduct,getProductImages])
const handleFilesAdded=useCallback(async(files:File[])=>{
setUploadError(null)
const{processed,rejected}=await processImageFiles(files)
if(rejected.length>0)setUploadError(`Unsupported files: ${rejected.join(', ')}`)
setNewImages(prev=>[...prev,...processed])
},[])
const handleDropError=useCallback((err:Error)=>{setUploadError(err.message||'Failed to add files.')},[])
const handleDeleteExisting=(path:string)=>{setImagesToDelete(prev=>[...prev,path]);setExistingImages(prev=>prev.filter(img=>img.path!==path))}
const handleDeleteNew=(index:number)=>setNewImages(prev=>prev.filter((_,i)=>i!==index))
const handleSetPrimary=(path:string)=>{setExistingImages(prev=>prev.map(img=>({...img,isPrimary:img.path===path})).sort((a,b)=>(b.isPrimary?1:0)-(a.isPrimary?1:0)))}
const{execute:save,isLoading:isSaving,error:saveError,clearError}=useAsyncAction(async()=>{
if(!name.trim())throw new Error('Please enter a product name.')
const remainingExisting=existingImages.filter(img=>!imagesToDelete.includes(img.path))
if(remainingExisting.length===0&&newImages.length===0)throw new Error('Product must have at least one image.')
await updateProduct(productSlug,name.trim(),description.trim())
for(const path of imagesToDelete){const filename=path.split('/').pop()||'';await deleteProductImage(productSlug,filename)}
for(const{file,base64}of newImages){await uploadProductImage(productSlug,file.name,base64)}
const newPrimary=existingImages.find(img=>img.isPrimary&&!imagesToDelete.includes(img.path))
if(newPrimary&&originalProduct&&newPrimary.path!==originalProduct.primary_image){const filename=newPrimary.path.split('/').pop()||'';await setPrimaryProductImage(productSlug,filename)}
await refresh();toast.success(`Product "${name.trim()}" updated`);onOpenChange(false)
})
const handleClose=useCallback(()=>{if(!isSaving){onOpenChange(false);clearError();setUploadError(null)}},[isSaving,onOpenChange,clearError])
const hasChanges=originalProduct&&(name.trim()!==originalProduct.name||description.trim()!==originalProduct.description||newImages.length>0||imagesToDelete.length>0||existingImages.some(img=>img.isPrimary&&img.path!==originalProduct.primary_image))
const visibleExistingImages=existingImages.filter(img=>!imagesToDelete.includes(img.path))
const isWorking=isLoading||isSaving
const error=loadError||saveError||uploadError
const loadingMsg=isLoading?'Loading product...':'Saving changes...'
return(<FormDialog open={open} onOpenChange={handleClose} title="Edit Product" description="Update product details and images." icon={<Package className="h-5 w-5"/>} iconColor="text-brand-500" isLoading={isWorking} loadingMessage={loadingMsg} error={error} onClearError={()=>{clearError();setUploadError(null)}} maxWidth="max-w-lg" footer={<>
<Button variant="outline" onClick={handleClose} disabled={isSaving}>Cancel</Button>
<Button onClick={()=>save()} disabled={isWorking||!name.trim()||!hasChanges} className="bg-brand-500 hover:bg-brand-600">{isSaving?'Saving...':'Save Changes'}</Button>
</>}>
{/* Name Input */}
<div className="space-y-2">
<label htmlFor="edit-product-name" className="text-sm font-medium">Name <span className="text-destructive">*</span></label>
<Input id="edit-product-name" value={name} onChange={(e)=>setName(e.target.value)} placeholder="e.g., Night Cream 50ml" autoFocus/>
</div>
{/* Description Input */}
<div className="space-y-2">
<label htmlFor="edit-product-description" className="text-sm font-medium">Description</label>
<textarea id="edit-product-description" value={description} onChange={(e)=>setDescription(e.target.value)} placeholder="Describe the product (size, texture, use cases, etc.)" rows={3} className="w-full px-3 py-2 text-sm border rounded-md bg-transparent focus:outline-none focus:ring-2 focus:ring-brand-500 resize-none"/>
</div>
{/* Product Images */}
<div className="space-y-2">
<label className="text-sm font-medium">Product Images <span className="text-destructive">*</span></label>
{/* Existing Images */}
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
{/* New Images */}
{newImages.length>0&&(<div className="flex flex-wrap gap-2 mb-2">
{newImages.map((item,index)=>(<div key={index} className="relative group">
<img src={item.dataUrl} alt={item.file.name} className="h-20 w-20 rounded object-cover border border-dashed border-success"/>
<div className="absolute top-1 right-1 bg-success text-white text-[10px] px-1 rounded">NEW</div>
<button type="button" onClick={()=>handleDeleteNew(index)} className="absolute -top-1 -right-1 h-5 w-5 bg-destructive text-white rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"><X className="h-3 w-3"/></button>
<span className="absolute bottom-0 left-0 right-0 bg-black/60 text-white text-[10px] px-1 truncate rounded-b">{item.file.name}</span>
</div>))}
</div>)}
{/* Dropzone */}
<Dropzone accept={{'image/*':getAllowedImageExts().map(e=>e)}} maxFiles={20} onDrop={handleFilesAdded} onError={handleDropError} className="border-dashed p-3">
<DropzoneEmptyState><div className="flex flex-col items-center"><p className="text-xs mb-1">Drop images to add</p></div></DropzoneEmptyState>
</Dropzone>
                <p className="text-xs text-muted-foreground">Click the star to set the primary image. The primary image is used first, with additional images included as extra references.</p>
</div>
</FormDialog>)}
