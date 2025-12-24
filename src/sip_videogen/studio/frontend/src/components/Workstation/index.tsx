//Workstation component - image review and curation workspace
import{useWorkstation}from'../../context/WorkstationContext'
import{ImageDisplay}from'./ImageDisplay'
import{ThumbnailStrip}from'./ThumbnailStrip'
export function Workstation(){
const{currentBatch}=useWorkstation()
const hasImages=currentBatch.length>0
return(<div className="flex-1 flex flex-col bg-secondary/20 dark:bg-secondary/10">{hasImages?(<><ImageDisplay/><ThumbnailStrip/></>):(<div className="flex-1 flex items-center justify-center"><div className="text-center"><h2 className="text-lg font-medium text-muted-foreground">Workstation</h2><p className="text-sm text-muted-foreground/60 mt-1">Image review and curation</p></div></div>)}</div>)}
