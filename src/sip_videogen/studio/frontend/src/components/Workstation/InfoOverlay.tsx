//InfoOverlay - shows image metadata (dimensions, date, prompt) when toggled
import{useViewer}from'../../context/ViewerContext'
import{useWorkstation}from'../../context/WorkstationContext'
export function InfoOverlay(){
const{showInfo,naturalW,naturalH}=useViewer()
const{currentBatch,selectedIndex}=useWorkstation()
const img=currentBatch[selectedIndex]
if(!showInfo)return null
return(<div className="absolute bottom-4 left-4 z-20 bg-black/70 backdrop-blur-sm text-white text-xs p-3 rounded-lg max-w-xs space-y-1">
<div>{naturalW&&naturalH?`${naturalW} × ${naturalH}`:'Loading...'}</div>
<div>{img?.timestamp?new Date(img.timestamp).toLocaleString():'Unknown date'}</div>
{img?.prompt&&(<p style={{WebkitLineClamp:3,display:'-webkit-box',WebkitBoxOrient:'vertical',overflow:'hidden'}}>{img.prompt}</p>)}
</div>)
}
