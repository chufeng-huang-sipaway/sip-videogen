//Reusable dialog shell for form dialogs with loading and error states
import*as React from'react'
import{Dialog,DialogContent,DialogDescription,DialogFooter,DialogHeader,DialogTitle}from'./dialog'
import{Alert,AlertDescription}from'./alert'
import{Spinner}from'./spinner'
export interface FormDialogProps{open:boolean;onOpenChange:(open:boolean)=>void;title:string;description?:string;icon?:React.ReactNode;iconColor?:string;isLoading?:boolean;loadingMessage?:string;error?:string|null;onClearError?:()=>void;children:React.ReactNode;footer?:React.ReactNode;preventCloseWhileLoading?:boolean;maxWidth?:string}
export function FormDialog({open,onOpenChange,title,description,icon,iconColor='text-brand-500',isLoading=false,loadingMessage='Loading...',error,onClearError,children,footer,preventCloseWhileLoading=true,maxWidth='max-w-md'}:FormDialogProps){
const handleOpenChange=(val:boolean)=>{if(!val&&isLoading&&preventCloseWhileLoading)return;if(!val)onClearError?.();onOpenChange(val)}
return(<Dialog open={open} onOpenChange={handleOpenChange}>
<DialogContent className={maxWidth}>
<DialogHeader>
<DialogTitle className="flex items-center gap-2">{icon&&<span className={iconColor}>{icon}</span>}{title}</DialogTitle>
{description&&<DialogDescription>{description}</DialogDescription>}
</DialogHeader>
{isLoading?(<div className="py-8 flex flex-col items-center gap-3"><Spinner className={`h-6 w-6 ${iconColor}`}/><p className="text-sm text-muted-foreground">{loadingMessage}</p></div>
):(<div className="space-y-4">{children}{error&&(<Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>)}</div>)}
{footer&&<DialogFooter>{footer}</DialogFooter>}
</DialogContent>
</Dialog>)}
