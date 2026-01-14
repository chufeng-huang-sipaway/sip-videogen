//InfoOverlay - shows image metadata (dimensions, date, prompt) when toggled
import{useViewer}from'../../context/ViewerContext'
import{useWorkstation}from'../../context/WorkstationContext'
export function InfoOverlay(){
const{showInfo,toggleInfo,naturalW,naturalH}=useViewer()
const{currentBatch,selectedIndex}=useWorkstation()
const img=currentBatch[selectedIndex]
if(!showInfo)return null
return(<div onClick={toggleInfo} title="Click to dismiss (or press I)" className="absolute bottom-4 left-4 z-20 bg-black/70 backdrop-blur-sm text-white text-xs p-3 rounded-lg max-w-xs space-y-1 cursor-pointer hover:bg-black/80 transition-colors">
<div>{naturalW&&naturalH?`${naturalW} × ${naturalH}`:'Loading...'}</div>
<div>{img?.timestamp?new Date(img.timestamp).toLocaleString():'Unknown date'}</div>
{img?.prompt&&(<p style={{WebkitLineClamp:3,display:'-webkit-box',WebkitBoxOrient:'vertical',overflow:'hidden'}}>{img.prompt}</p>)}
</div>)
}
