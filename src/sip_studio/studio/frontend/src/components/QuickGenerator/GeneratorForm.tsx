//Form for quick image generation parameters
import type{ProductEntry,StyleReferenceSummary}from'@/lib/bridge'
interface Props{
  products:ProductEntry[]
  styleRefs:StyleReferenceSummary[]
  selectedProduct:string
  selectedStyleRef:string
  aspectRatio:string
  count:number
  prompt:string
  generating:boolean
  onProductChange:(v:string)=>void
  onStyleRefChange:(v:string)=>void
  onAspectRatioChange:(v:string)=>void
  onCountChange:(v:number)=>void
  onPromptChange:(v:string)=>void
  onGenerate:()=>void
}
export function GeneratorForm({products,styleRefs,selectedProduct,selectedStyleRef,aspectRatio,count,prompt,generating,onProductChange,onStyleRefChange,onAspectRatioChange,onCountChange,onPromptChange,onGenerate}:Props){
return(<div className="generator-form">
<div className="form-group"><label>Prompt</label><textarea value={prompt} onChange={e=>onPromptChange(e.target.value)} rows={3} placeholder="Describe the image..." disabled={generating}/></div>
<div className="form-row">
<div className="form-group"><label>Product (optional)</label><select value={selectedProduct} onChange={e=>onProductChange(e.target.value)} disabled={generating}><option value="">None</option>{products.map(p=><option key={p.slug} value={p.slug}>{p.name}</option>)}</select></div>
<div className="form-group"><label>Style Reference (optional)</label><select value={selectedStyleRef} onChange={e=>onStyleRefChange(e.target.value)} disabled={generating}><option value="">None</option>{styleRefs.map(s=><option key={s.slug} value={s.slug}>{s.name}</option>)}</select></div>
</div>
<div className="form-row">
<div className="form-group"><label>Aspect Ratio</label><select value={aspectRatio} onChange={e=>onAspectRatioChange(e.target.value)} disabled={generating}><option value="1:1">1:1 Square</option><option value="16:9">16:9 Landscape</option><option value="9:16">9:16 Portrait</option><option value="4:3">4:3</option><option value="3:4">3:4</option></select></div>
<div className="form-group"><label>Count (1-10)</label><input type="number" min={1} max={10} value={count} onChange={e=>onCountChange(parseInt(e.target.value)||1)} disabled={generating}/></div>
</div>
<button className="generate-btn primary" onClick={onGenerate} disabled={generating||!prompt.trim()}>{generating?'Generating...':`Generate ${count} Image${count>1?'s':''}`}</button>
</div>)}
