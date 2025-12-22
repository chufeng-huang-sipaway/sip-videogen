//Toast notification wrapper using sonner
import{Toaster as SonnerToaster}from'sonner'
export function Toaster(){return(<SonnerToaster position="top-right" closeButton richColors toastOptions={{className:'text-sm',duration:5000}}/>)}
export{toast}from'sonner'
