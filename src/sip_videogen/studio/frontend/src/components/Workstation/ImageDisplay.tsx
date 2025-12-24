//ImageDisplay component - displays the currently selected image
import{useWorkstation}from'../../context/WorkstationContext'
export function ImageDisplay(){
const{currentBatch,selectedIndex}=useWorkstation()
const currentImage=currentBatch[selectedIndex]
if(!currentImage)return null
return(<div className="flex-1 flex items-center justify-center p-4 bg-secondary/10 dark:bg-secondary/5"><img src={currentImage.path.startsWith('/')?`file://${currentImage.path}`:currentImage.path} alt={currentImage.prompt||'Generated image'} className="max-w-full max-h-full object-contain rounded-lg shadow-md"/></div>)}
