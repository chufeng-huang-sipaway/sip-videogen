//Playground mode for quick image generation (image-only, no video support)
import{useState,useEffect}from'react'
import{Plus,Zap,Loader2,AlertCircle}from'lucide-react'
import{Button}from'@/components/ui/button'
import{Alert,AlertDescription}from'@/components/ui/alert'
import{AspectRatioSelector}from'@/components/ChatPanel/AspectRatioSelector'
import{PreviewCanvas}from'./PreviewCanvas'
import{bridge}from'@/lib/bridge'
import{useProducts}from'@/context/ProductContext'
import{useStyleReferences}from'@/context/StyleReferenceContext'
import{type AspectRatio,isValidAspectRatio}from'@/types/aspectRatio'
//LocalStorage helpers with safety
const STORAGE_KEY='playground-aspect-ratio'
function getStoredAspectRatio():AspectRatio{
try{const v=localStorage.getItem(STORAGE_KEY);return v&&isValidAspectRatio(v)?v:'1:1'}catch{return'1:1'}}
function setStoredAspectRatio(v:AspectRatio):void{try{localStorage.setItem(STORAGE_KEY,v)}catch{}}
interface PlaygroundModeProps{brandSlug:string|null}
export function PlaygroundMode({brandSlug}:PlaygroundModeProps){
const[prompt,setPrompt]=useState('')
const[selectedProduct,setSelectedProduct]=useState('')
const[selectedStyleRef,setSelectedStyleRef]=useState('')
const[aspectRatio,setAspectRatio]=useState<AspectRatio>(getStoredAspectRatio)
const[isGenerating,setIsGenerating]=useState(false)
const[result,setResult]=useState<{path:string;data?:string}|null>(null)
const[error,setError]=useState<string|null>(null)
//Brand-aware hooks for products/styles
const{products}=useProducts()
const{styleReferences}=useStyleReferences()
//Reset selections when brandSlug changes
useEffect(()=>{setSelectedProduct('');setSelectedStyleRef('')},[brandSlug])
//Persist aspect ratio
useEffect(()=>{setStoredAspectRatio(aspectRatio)},[aspectRatio])
const handleGenerate=async()=>{
if(!prompt.trim())return
setIsGenerating(true);setError(null);setResult(null)
try{
const res=await bridge.quickGenerate(prompt,selectedProduct||undefined,selectedStyleRef||undefined,aspectRatio,1)
if(res.images?.[0])setResult(res.images[0])
else if(res.error)setError(res.error)
else if(res.errors?.[0])setError(res.errors[0].error)
}catch(e){setError(e instanceof Error?e.message:String(e))}
finally{setIsGenerating(false)}}
const handleNewGeneration=()=>{setResult(null);setPrompt('')}
//No brand selected state
if(!brandSlug)return(
<div className="flex flex-col items-center justify-center h-full text-center p-8">
<div className="text-muted-foreground text-sm">Select a brand to use Playground</div>
</div>)
return(
<div className="flex flex-col h-full">
<div className="flex-1 flex items-center justify-center overflow-hidden">
<PreviewCanvas aspectRatio={aspectRatio} isLoading={isGenerating} result={result}/>
</div>
{/* New Generation button (when result exists) */}
{result&&!isGenerating&&(
<div className="flex justify-center py-3">
<Button variant="outline" onClick={handleNewGeneration}>
<Plus className="w-4 h-4 mr-2"/>New Generation
</Button>
</div>)}
{error&&(<div className="px-4 pb-2">
<Alert variant="destructive"><AlertCircle className="h-4 w-4"/><AlertDescription>{error}</AlertDescription></Alert>
</div>)}
{/* Controls */}
<div className="p-4 space-y-3 border-t border-border/20">
{/* Aspect Ratio only (no video toggle in Playground) */}
<div className="flex items-center gap-3">
<AspectRatioSelector value={aspectRatio} onChange={setAspectRatio} generationMode="image"/>
</div>
{/* Product + Style selectors */}
<div className="flex items-center gap-2">
<select value={selectedProduct} onChange={e=>setSelectedProduct(e.target.value)} className="flex-1 px-3 py-1.5 rounded-lg border border-border/40 text-sm bg-background">
<option value="">No product</option>
{products.map(p=><option key={p.slug} value={p.slug}>{p.name}</option>)}
</select>
<select value={selectedStyleRef} onChange={e=>setSelectedStyleRef(e.target.value)} className="flex-1 px-3 py-1.5 rounded-lg border border-border/40 text-sm bg-background">
<option value="">No style</option>
{styleReferences.map(s=><option key={s.slug} value={s.slug}>{s.name}</option>)}
</select>
</div>
{/* Prompt input + generate */}
<div className="flex items-end gap-2">
<textarea value={prompt} onChange={e=>setPrompt(e.target.value)} placeholder="Describe your image..." rows={2} disabled={isGenerating} className="flex-1 px-4 py-3 rounded-xl border border-border/40 resize-none text-sm bg-background focus:outline-none focus:ring-2 focus:ring-ring"/>
<Button onClick={handleGenerate} disabled={isGenerating||!prompt.trim()} className="px-6 h-[52px]">
{isGenerating?<Loader2 className="w-4 h-4 animate-spin"/>:<Zap className="w-4 h-4"/>}
</Button>
</div>
</div>
</div>)}
