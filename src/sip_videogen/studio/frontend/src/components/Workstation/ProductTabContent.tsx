//ProductTabContent - inline editing view for product tabs
import{useCallback,useRef,useEffect,useState,useMemo}from'react'
import{Package,X,Star,Loader2,Trash2,Plus,Save,AlertTriangle}from'lucide-react'
import{Button}from'@/components/ui/button'
import{Input}from'@/components/ui/input'
import{Dropzone,DropzoneEmptyState}from'@/components/ui/dropzone'
import{AlertDialog,AlertDialogAction,AlertDialogCancel,AlertDialogContent,AlertDialogDescription,AlertDialogFooter,AlertDialogHeader,AlertDialogTitle}from'@/components/ui/alert-dialog'
import{useProducts}from'@/context/ProductContext'
import{useTabs}from'@/context/TabContext'
import{useBrand}from'@/context/BrandContext'
import{makeTabId}from'@/types/tabs'
import{processImageFiles}from'@/lib/file-utils'
import type{ProcessedFile}from'@/lib/file-utils'
import{bridge,isPyWebView}from'@/lib/bridge'
import{getAllowedImageExts}from'@/lib/constants'
import{toast}from'@/components/ui/toaster'
import type{ProductFull,ProductAttribute}from'@/lib/bridge'
import{cn}from'@/lib/utils'
interface Props{productSlug:string;isActive:boolean}
type LoadState='loading'|'loaded'|'error'|'not-found'
interface ExistingImage{path:string;filename:string;thumbnailUrl:string|null;isPrimary:boolean}
export function ProductTabContent({productSlug,isActive}:Props){
const{activeBrand}=useBrand()
const{getProduct,getProductImages,updateProduct,uploadProductImage,deleteProductImage,setPrimaryProductImage,deleteProduct,refresh}=useProducts()
const{setTabDirty,updateTabTitle,closeTab}=useTabs()
//Compute tab ID from brand + type + slug
const tabId=useMemo(()=>activeBrand?makeTabId(activeBrand,'product',productSlug):'',[activeBrand,productSlug])
const[loadState,setLoadState]=useState<LoadState>('loading')
const[error,setError]=useState<string|null>(null)
const[originalProduct,setOriginalProduct]=useState<ProductFull|null>(null)
//Editable fields
const[name,setName]=useState('')
const[description,setDescription]=useState('')
const[attributes,setAttributes]=useState<ProductAttribute[]>([])
//Image management
const[existingImages,setExistingImages]=useState<ExistingImage[]>([])
const[newImages,setNewImages]=useState<ProcessedFile[]>([])
const[imagesToDelete,setImagesToDelete]=useState<string[]>([])
const[uploadError,setUploadError]=useState<string|null>(null)
//Saving/Deleting state
const[isSaving,setIsSaving]=useState(false)
const[showDeleteConfirm,setShowDeleteConfirm]=useState(false)
const[isDeleting,setIsDeleting]=useState(false)
//Race condition handling
const requestIdRef=useRef(0)
//Compute dirty state
const isDirty=originalProduct!==null&&(name.trim()!==originalProduct.name||description.trim()!==originalProduct.description||newImages.length>0||imagesToDelete.length>0||existingImages.some(img=>img.isPrimary&&img.path!==originalProduct.primary_image)||JSON.stringify(attributes)!==JSON.stringify(originalProduct.attributes))
//Update dirty state in TabContext
useEffect(()=>{if(!isActive||!tabId)return
setTabDirty(tabId,isDirty)},[isActive,tabId,isDirty,setTabDirty])
//Load product data
useEffect(()=>{if(!isActive)return
const thisRequestId=++requestIdRef.current
setLoadState('loading');setError(null);setNewImages([]);setImagesToDelete([])
async function load(){
try{const[product,imagePaths]=await Promise.all([getProduct(productSlug),getProductImages(productSlug)])
if(requestIdRef.current!==thisRequestId)return
setOriginalProduct(product);setName(product.name);setDescription(product.description);setAttributes([...product.attributes])
//Build image list with thumbnails
const images:ExistingImage[]=[]
for(const path of imagePaths){const filename=path.split('/').pop()||path
let thumbnailUrl:string|null=null
if(isPyWebView()){try{thumbnailUrl=await bridge.getProductImageThumbnail(path)}catch{}}
images.push({path,filename,thumbnailUrl,isPrimary:path===product.primary_image})}
if(requestIdRef.current!==thisRequestId)return
images.sort((a,b)=>(b.isPrimary?1:0)-(a.isPrimary?1:0))
setExistingImages(images);setLoadState('loaded')
}catch(e){if(requestIdRef.current!==thisRequestId)return
const msg=e instanceof Error?e.message:'Failed to load product'
if(msg.toLowerCase().includes('not found')){setLoadState('not-found')}else{setError(msg);setLoadState('error')}}}
load()
return()=>{requestIdRef.current++}},[productSlug,isActive,getProduct,getProductImages])
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
//Attribute management
const handleAddAttribute=()=>{setAttributes(prev=>[...prev,{key:'',value:'',category:'general'}])}
const handleRemoveAttribute=(index:number)=>{setAttributes(prev=>prev.filter((_,i)=>i!==index))}
const handleAttributeChange=(index:number,field:'key'|'value'|'category',val:string)=>{setAttributes(prev=>prev.map((attr,i)=>i===index?{...attr,[field]:val}:attr))}
//Save handler
const handleSave=async()=>{if(!name.trim()){toast.error('Please enter a product name');return}
const remainingExisting=existingImages.filter(img=>!imagesToDelete.includes(img.path))
if(remainingExisting.length===0&&newImages.length===0){toast.error('Product must have at least one image');return}
setIsSaving(true)
try{
//Update product metadata
await updateProduct(productSlug,name.trim(),description.trim(),attributes.filter(a=>a.key.trim()!==''))
//Delete removed images
for(const path of imagesToDelete){const filename=path.split('/').pop()||'';await deleteProductImage(productSlug,filename)}
//Upload new images
for(const{file,base64}of newImages){await uploadProductImage(productSlug,file.name,base64)}
//Set primary if changed
const newPrimary=existingImages.find(img=>img.isPrimary&&!imagesToDelete.includes(img.path))
if(newPrimary&&originalProduct&&newPrimary.path!==originalProduct.primary_image){const filename=newPrimary.path.split('/').pop()||'';await setPrimaryProductImage(productSlug,filename)}
await refresh()
//Update tab title if name changed
if(name.trim()!==originalProduct?.name&&tabId){updateTabTitle(tabId,name.trim())}
//Reload to get fresh state
const[product,imagePaths]=await Promise.all([getProduct(productSlug),getProductImages(productSlug)])
setOriginalProduct(product);setName(product.name);setDescription(product.description);setAttributes([...product.attributes])
const images:ExistingImage[]=[]
for(const path of imagePaths){const filename=path.split('/').pop()||path
let thumbnailUrl:string|null=null
if(isPyWebView()){try{thumbnailUrl=await bridge.getProductImageThumbnail(path)}catch{}}
images.push({path,filename,thumbnailUrl,isPrimary:path===product.primary_image})}
images.sort((a,b)=>(b.isPrimary?1:0)-(a.isPrimary?1:0))
setExistingImages(images);setNewImages([]);setImagesToDelete([])
toast.success(`Product "${name.trim()}" saved`)
}catch(e){toast.error(e instanceof Error?e.message:'Failed to save product')
}finally{setIsSaving(false)}}
//Delete handler
const handleDelete=async()=>{setIsDeleting(true)
try{await deleteProduct(productSlug);if(tabId)closeTab(tabId);toast.success('Product deleted')
}catch(e){toast.error(e instanceof Error?e.message:'Failed to delete product')
}finally{setIsDeleting(false);setShowDeleteConfirm(false)}}
//Retry handler
const handleRetry=()=>{setLoadState('loading');requestIdRef.current++}
//Loading state
if(loadState==='loading')return(<div className="flex-1 flex items-center justify-center"><Loader2 className="w-8 h-8 animate-spin text-muted-foreground/50"/></div>)
//Error state
if(loadState==='error')return(<div className="flex-1 flex flex-col items-center justify-center gap-4"><AlertTriangle className="w-8 h-8 text-destructive/50"/><p className="text-sm text-muted-foreground">{error||'Failed to load product'}</p><Button variant="outline" size="sm" onClick={handleRetry}>Retry</Button></div>)
//Not found state
if(loadState==='not-found')return(<div className="flex-1 flex flex-col items-center justify-center gap-4"><Package className="w-12 h-12 text-muted-foreground/30"/><p className="text-sm text-muted-foreground">Product not found</p><p className="text-xs text-muted-foreground/60">It may have been deleted</p><Button variant="outline" size="sm" onClick={()=>{if(tabId)closeTab(tabId)}}>Close Tab</Button></div>)
const visibleExistingImages=existingImages.filter(img=>!imagesToDelete.includes(img.path))
//Loaded state - inline editing view
return(<div className="flex-1 flex flex-col min-h-0 overflow-hidden">
{/* Header */}
<div className="flex-shrink-0 border-b bg-background/95 backdrop-blur-sm px-6 py-4">
<div className="flex items-center justify-between">
<div className="flex items-center gap-3"><Package className="w-5 h-5 text-purple-500"/><h1 className="text-lg font-semibold">{originalProduct?.name||'Product'}</h1>{isDirty&&<span className="text-blue-500">•</span>}</div>
<div className="flex items-center gap-2">
<Button variant="outline" size="sm" onClick={()=>setShowDeleteConfirm(true)} className="text-destructive hover:text-destructive"><Trash2 className="w-4 h-4 mr-1"/>Delete</Button>
<Button size="sm" onClick={handleSave} disabled={isSaving||!isDirty} className="bg-purple-600 hover:bg-purple-700"><Save className="w-4 h-4 mr-1"/>{isSaving?'Saving...':'Save'}</Button>
</div>
</div>
</div>
{/* Content */}
<div className="flex-1 overflow-y-auto p-6">
<div className="max-w-2xl mx-auto space-y-6">
{/* Name */}
<div className="space-y-2">
<label htmlFor="product-name" className="text-sm font-medium">Name <span className="text-red-500">*</span></label>
<Input id="product-name" value={name} onChange={e=>setName(e.target.value)} placeholder="e.g., Night Cream 50ml"/>
</div>
{/* Description */}
<div className="space-y-2">
<label htmlFor="product-desc" className="text-sm font-medium">Description</label>
<textarea id="product-desc" value={description} onChange={e=>setDescription(e.target.value)} placeholder="Describe the product..." rows={3} className="w-full px-3 py-2 text-sm border rounded-md bg-transparent focus:outline-none focus:ring-2 focus:ring-purple-500 resize-none"/>
</div>
{/* Images */}
<div className="space-y-3">
<label className="text-sm font-medium">Product Images <span className="text-red-500">*</span></label>
{uploadError&&<p className="text-sm text-destructive">{uploadError}</p>}
{/* Existing Images */}
{visibleExistingImages.length>0&&(<div className="flex flex-wrap gap-2">
{visibleExistingImages.map(img=>(<div key={img.path} className={cn("relative group rounded-lg overflow-hidden",img.isPrimary?"ring-2 ring-purple-500 ring-offset-2":"")}>
{img.thumbnailUrl?<img src={img.thumbnailUrl} alt={img.filename} className="h-24 w-24 object-cover"/>:<div className="h-24 w-24 bg-muted flex items-center justify-center"><Loader2 className="w-4 h-4 animate-spin text-muted-foreground"/></div>}
{img.isPrimary&&<div className="absolute top-1 left-1 bg-purple-500 text-white rounded-full p-0.5"><Star className="h-3 w-3 fill-current"/></div>}
<div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-1">
{!img.isPrimary&&<button type="button" onClick={()=>handleSetPrimary(img.path)} className="h-7 w-7 bg-purple-500 text-white rounded-full flex items-center justify-center hover:bg-purple-600" title="Set as primary"><Star className="h-3.5 w-3.5"/></button>}
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
{/* Attributes */}
<div className="space-y-3">
<div className="flex items-center justify-between"><label className="text-sm font-medium">Attributes</label><Button variant="ghost" size="sm" onClick={handleAddAttribute}><Plus className="w-4 h-4 mr-1"/>Add</Button></div>
{attributes.length===0?<p className="text-sm text-muted-foreground/60">No attributes yet</p>:(
<div className="space-y-2">
{attributes.map((attr,i)=>(<div key={i} className="flex items-center gap-2">
<Input value={attr.key} onChange={e=>handleAttributeChange(i,'key',e.target.value)} placeholder="Key" className="flex-1"/>
<Input value={attr.value} onChange={e=>handleAttributeChange(i,'value',e.target.value)} placeholder="Value" className="flex-1"/>
<select value={attr.category} onChange={e=>handleAttributeChange(i,'category',e.target.value)} className="px-2 py-1.5 text-sm border rounded-md bg-transparent">
<option value="general">General</option><option value="physical">Physical</option><option value="ingredients">Ingredients</option><option value="usage">Usage</option>
</select>
<Button variant="ghost" size="icon" onClick={()=>handleRemoveAttribute(i)} className="text-destructive hover:text-destructive"><X className="w-4 h-4"/></Button>
</div>))}
</div>)}
</div>
</div>
</div>
{/* Delete Confirmation Dialog */}
<AlertDialog open={showDeleteConfirm} onOpenChange={setShowDeleteConfirm}>
<AlertDialogContent>
<AlertDialogHeader><AlertDialogTitle>Delete Product</AlertDialogTitle><AlertDialogDescription>Are you sure you want to delete "{originalProduct?.name}"? This action cannot be undone.</AlertDialogDescription></AlertDialogHeader>
<AlertDialogFooter><AlertDialogCancel disabled={isDeleting}>Cancel</AlertDialogCancel><AlertDialogAction onClick={handleDelete} disabled={isDeleting} className="bg-destructive hover:bg-destructive/90">{isDeleting?'Deleting...':'Delete'}</AlertDialogAction></AlertDialogFooter>
</AlertDialogContent>
</AlertDialog>
</div>)}
