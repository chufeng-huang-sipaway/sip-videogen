//Results grid for displaying generated images
import type{QuickGenerateResult}from'@/lib/bridge'
interface Props{
  result:QuickGenerateResult
  onDownload:(img:{path:string;data?:string})=>void
  onDownloadAll:()=>void
  onRegenerate:()=>void
  onNewPrompt:()=>void
}
export function ResultsGrid({result,onDownload,onDownloadAll,onRegenerate,onNewPrompt}:Props){
return(<div className="results-grid">
<div className="results-summary">{result.generated}/{result.requested} images generated</div>
{result.errors&&result.errors.length>0&&(<div className="results-errors">{result.errors.map(e=><div key={e.index}>Image {e.index+1}: {e.error}</div>)}</div>)}
<div className="results-images">{result.images.map((img,i)=>(<div key={i} className="result-image"><img src={img.data||img.path} alt={`Generated ${i+1}`}/><button onClick={()=>onDownload(img)} className="download-btn">Download</button></div>))}</div>
<div className="results-actions"><button onClick={onDownloadAll}>Download All</button><button onClick={onRegenerate}>Regenerate</button><button onClick={onNewPrompt}>New Prompt</button></div>
</div>)}
