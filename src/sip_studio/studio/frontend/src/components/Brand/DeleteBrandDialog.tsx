import{useCallback}from'react'
import{Trash2}from'lucide-react'
import{Button}from'@/components/ui/button'
import{FormDialog}from'@/components/ui/form-dialog'
import{bridge,isPyWebView}from'@/lib/bridge'
import type{BrandEntry}from'@/lib/bridge'
import{useAsyncAction}from'@/hooks/useAsyncAction'
import{toast}from'@/components/ui/toaster'
interface DeleteBrandDialogProps{brand:BrandEntry|null;open:boolean;onOpenChange:(open:boolean)=>void;onDeleted:()=>void}
export function DeleteBrandDialog({brand,open,onOpenChange,onDeleted}:DeleteBrandDialogProps){
const{execute,isLoading,error,clearError}=useAsyncAction(async()=>{
if(!brand)return
if(isPyWebView())await bridge.deleteBrand(brand.slug)
toast.success(`Brand "${brand.name}" deleted`);onDeleted();onOpenChange(false)
})
const handleClose=useCallback(()=>{if(!isLoading){onOpenChange(false);clearError()}},[isLoading,onOpenChange,clearError])
if(!brand)return null
return(<FormDialog open={open} onOpenChange={handleClose} title="Delete Brand" description={`Are you sure you want to delete "${brand.name}"?`} icon={<Trash2 className="h-5 w-5"/>} iconColor="text-destructive" isLoading={isLoading} loadingMessage="Deleting brand..." error={error} onClearError={clearError} footer={<>
<Button variant="outline" onClick={handleClose} disabled={isLoading}>Cancel</Button>
<Button variant="destructive" onClick={()=>execute()} disabled={isLoading}>{isLoading?'Deleting...':'Delete Brand'}</Button>
</>}>
<div className="py-2">
<p className="text-sm text-muted-foreground mb-3">This will permanently remove:</p>
<ul className="text-sm text-muted-foreground space-y-1 list-disc list-inside">
<li>All brand identity data</li>
<li>All uploaded assets and documents</li>
<li>All generated images</li>
</ul>
<p className="text-sm font-medium text-destructive mt-4">This action cannot be undone.</p>
</div>
</FormDialog>)}
