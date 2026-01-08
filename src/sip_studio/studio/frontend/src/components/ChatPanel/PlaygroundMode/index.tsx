//Playground mode for quick image generation (image-only, no video support)
import{useState,useEffect,useRef}from'react'
import{Zap,AlertCircle,X}from'lucide-react'
import{Button}from'@/components/ui/button'
import{Alert,AlertDescription}from'@/components/ui/alert'
import{AspectRatioSelector}from'@/components/ChatPanel/AspectRatioSelector'
import{CapsuleSelector}from'./CapsuleSelector'
import{PreviewCanvas}from'./PreviewCanvas'
import{bridge}from'@/lib/bridge'
import{useProducts}from'@/context/ProductContext'
import{useStyleReferences}from'@/context/StyleReferenceContext'
import{useWorkstation}from'@/context/WorkstationContext'
import{type AspectRatio,isValidAspectRatio}from'@/types/aspectRatio'
//LocalStorage helpers with safety
const STORAGE_KEY='playground-aspect-ratio'
function getStoredAspectRatio():AspectRatio{try{const v=localStorage.getItem(STORAGE_KEY);return v&&isValidAspectRatio(v)?v:'1:1'}catch{return'1:1'}}
function setStoredAspectRatio(v:AspectRatio):void{try{localStorage.setItem(STORAGE_KEY,v)}catch{/*ignore*/}}
interface PlaygroundModeProps{brandSlug:string|null}
export function PlaygroundMode({brandSlug}:PlaygroundModeProps){
const[prompt,setPrompt]=useState('')
const[selectedProduct,setSelectedProduct]=useState('')
const[selectedStyleRef,setSelectedStyleRef]=useState('')
const[aspectRatio,setAspectRatio]=useState<AspectRatio>(getStoredAspectRatio)
const[isGenerating,setIsGenerating]=useState(false)
const[isStopped,setIsStopped]=useState(false)
const[result,setResult]=useState<{path:string;data?:string}|null>(null)
const[error,setError]=useState<string|null>(null)
const abortRef=useRef(false)
//Brand-aware hooks for products/styles
const{products}=useProducts()
const{styleReferences}=useStyleReferences()
const{bumpStatusVersion}=useWorkstation()
//Reset selections when brandSlug changes
useEffect(()=>{setSelectedProduct('');setSelectedStyleRef('')},[brandSlug])
//Persist aspect ratio
useEffect(()=>{setStoredAspectRatio(aspectRatio)},[aspectRatio])
const handleGenerate=async()=>{
if(!prompt.trim())return
abortRef.current=false;setIsStopped(false)
setIsGenerating(true);setError(null);setResult(null)
try{
const res=await bridge.quickGenerate(prompt,selectedProduct||undefined,selectedStyleRef||undefined,aspectRatio,1)
if(abortRef.current){setIsGenerating(false);return}
if(res.images?.[0]){setResult(res.images[0]);bumpStatusVersion()}
else if(res.error)setError(res.error)
else if(res.errors?.[0])setError(res.errors[0].error)
}catch(e){if(!abortRef.current)setError(e instanceof Error?e.message:String(e))}
finally{setIsGenerating(false)}}
const handleStop=()=>{abortRef.current=true;setIsStopped(true);setIsGenerating(false)}
const handleClearPrompt=()=>{setPrompt('')}
//Map products/styles for CapsuleSelector
const productItems=products.map(p=>({slug:p.slug,name:p.name,description:p.description,imagePath:p.primary_image}))
const styleItems=styleReferences.map(s=>({slug:s.slug,name:s.name,description:s.description,imagePath:s.primary_image}))
//No brand selected state
if(!brandSlug)return(<div className="flex flex-col items-center justify-center h-full text-center p-8"><div className="text-muted-foreground text-sm">Select a brand to use Playground</div></div>)
return(<div className="flex flex-col h-full">
<div className="flex-1 flex items-center justify-center overflow-hidden">
<PreviewCanvas aspectRatio={aspectRatio} isLoading={isGenerating} result={result} onStop={handleStop}/>
</div>
{error&&(<div className="px-4 pb-2"><Alert variant="destructive"><AlertCircle className="h-4 w-4"/><AlertDescription>{error}</AlertDescription></Alert></div>)}
{isStopped&&!error&&(<div className="px-4 pb-2"><Alert><AlertDescription className="text-muted-foreground">Generation stopped</AlertDescription></Alert></div>)}
{/* Controls */}
<div className="p-4 space-y-3 border-t border-border/20">
{/* Selectors row: Aspect Ratio + Product + Style */}
<div className="flex items-center gap-2 flex-wrap">
<AspectRatioSelector value={aspectRatio} onChange={setAspectRatio} generationMode="image" disabled={isGenerating}/>
<CapsuleSelector items={productItems} value={selectedProduct} onChange={setSelectedProduct} disabled={isGenerating} placeholder="Product" emptyLabel="No product" type="product"/>
<CapsuleSelector items={styleItems} value={selectedStyleRef} onChange={setSelectedStyleRef} disabled={isGenerating} placeholder="Style" emptyLabel="No style" type="style"/>
</div>
{/* Prompt input + generate/stop */}
<div className="flex items-end gap-2">
<div className="relative flex-1">
<textarea value={prompt} onChange={e=>setPrompt(e.target.value)} placeholder="Describe your image..." rows={2} disabled={isGenerating} className="w-full px-4 py-3 pr-10 rounded-xl border border-border/40 resize-none text-sm bg-background focus:outline-none focus:ring-2 focus:ring-ring disabled:opacity-50 disabled:cursor-not-allowed"/>
{prompt&&!isGenerating&&(<button type="button" onClick={handleClearPrompt} className="absolute right-3 top-3 p-1 rounded-full hover:bg-muted transition-colors" title="Clear prompt"><X className="w-4 h-4 text-muted-foreground"/></button>)}
</div>
<Button onClick={handleGenerate} disabled={!prompt.trim()||isGenerating} className="px-6 h-[52px]"><Zap className="w-4 h-4"/></Button>
</div>
</div>
</div>)}
