//Quick image generator modal component
import{useState,useEffect}from'react'
import{bridge,type ProductEntry,type StyleReferenceSummary,type QuickGenerateResult}from'@/lib/bridge'
import{GeneratorForm}from'./GeneratorForm'
import{ResultsGrid}from'./ResultsGrid'
import'./QuickGenerator.css'
interface Props{brandSlug:string;onClose:()=>void}
function downloadImage(src:string,filename:string){const a=document.createElement('a');a.href=src;a.download=filename;a.click()}
export function QuickGenerator({brandSlug,onClose}:Props){
const[products,setProducts]=useState<ProductEntry[]>([])
const[styleRefs,setStyleRefs]=useState<StyleReferenceSummary[]>([])
const[selectedProduct,setSelectedProduct]=useState<string>('')
const[selectedStyleRef,setSelectedStyleRef]=useState<string>('')
const[aspectRatio,setAspectRatio]=useState<string>('1:1')
const[count,setCount]=useState(1)
const[prompt,setPrompt]=useState('')
const[generating,setGenerating]=useState(false)
const[results,setResults]=useState<QuickGenerateResult|null>(null)
const[error,setError]=useState<string|null>(null)
//Load products and style references on mount
useEffect(()=>{
bridge.getProducts(brandSlug).then(p=>setProducts(p||[])).catch(()=>setProducts([]))
bridge.getStyleReferences(brandSlug).then(s=>setStyleRefs(s||[])).catch(()=>setStyleRefs([]))
},[brandSlug])
const handleGenerate=async()=>{
if(!prompt.trim()){setError('Please enter a prompt');return}
setGenerating(true);setError(null);setResults(null)
try{
const result=await bridge.quickGenerate(prompt,selectedProduct||undefined,selectedStyleRef||undefined,aspectRatio,count)
setResults(result)
if(!result.success)setError(result.error||'Generation failed')
}catch(e){setError(String(e))}finally{setGenerating(false)}}
const handleClose=()=>{
if(results&&results.images.length>0){if(!window.confirm('Discard generated images?'))return}
onClose()}
return(<div className="quick-generator-modal">
<div className="quick-generator-header"><h3>Quick Generate</h3><button onClick={handleClose} className="close-btn">Close</button></div>
{error&&<div className="quick-generator-error">{error}</div>}
{!results?(<GeneratorForm products={products} styleRefs={styleRefs} selectedProduct={selectedProduct} selectedStyleRef={selectedStyleRef} aspectRatio={aspectRatio} count={count} prompt={prompt} generating={generating} onProductChange={setSelectedProduct} onStyleRefChange={setSelectedStyleRef} onAspectRatioChange={setAspectRatio} onCountChange={setCount} onPromptChange={setPrompt} onGenerate={handleGenerate}/>):(<ResultsGrid result={results} onDownload={(img)=>downloadImage(img.data||img.path,`generated-image-${Date.now()}.png`)} onDownloadAll={()=>results.images.forEach((img,i)=>downloadImage(img.data||img.path,`generated-${i+1}.png`))} onRegenerate={()=>{setResults(null);handleGenerate()}} onNewPrompt={()=>setResults(null)}/>)}
</div>)}
export{QuickGeneratorFAB}from'./QuickGeneratorFAB'
