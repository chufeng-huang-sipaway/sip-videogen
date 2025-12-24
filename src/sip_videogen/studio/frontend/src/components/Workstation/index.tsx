//Workstation component - image review and curation workspace
import{useCallback}from'react'
import{useWorkstation}from'../../context/WorkstationContext'
import{useBrand}from'../../context/BrandContext'
import{bridge}from'../../lib/bridge'
import{ImageDisplay}from'./ImageDisplay'
import{ThumbnailStrip}from'./ThumbnailStrip'
import{SwipeContainer}from'./SwipeContainer'
export function Workstation(){
const{currentBatch,selectedIndex,setCurrentBatch,setSelectedIndex,removeFromUnsorted}=useWorkstation()
const{activeBrand}=useBrand()
const hasImages=currentBatch.length>0
const currentImage=currentBatch[selectedIndex]
//Remove current image from batch and advance to next
const removeCurrentAndAdvance=useCallback(()=>{const newBatch=[...currentBatch];newBatch.splice(selectedIndex,1);setCurrentBatch(newBatch);if(selectedIndex>=newBatch.length&&newBatch.length>0)setSelectedIndex(newBatch.length-1)},[currentBatch,selectedIndex,setCurrentBatch,setSelectedIndex])
//Handle swipe right (keep)
const handleKeep=useCallback(async()=>{if(!currentImage||!activeBrand)return;try{await bridge.markImageKept(currentImage.id,activeBrand);removeFromUnsorted(currentImage.id);removeCurrentAndAdvance()}catch(e){console.error('Failed to mark image as kept:',e)}},[currentImage,activeBrand,removeFromUnsorted,removeCurrentAndAdvance])
//Handle swipe left (trash)
const handleTrash=useCallback(async()=>{if(!currentImage||!activeBrand)return;try{await bridge.markImageTrashed(currentImage.id,activeBrand);removeFromUnsorted(currentImage.id);removeCurrentAndAdvance()}catch(e){console.error('Failed to trash image:',e)}},[currentImage,activeBrand,removeFromUnsorted,removeCurrentAndAdvance])
return(<div className="flex-1 flex flex-col bg-secondary/20 dark:bg-secondary/10">{hasImages?(<><SwipeContainer onSwipeRight={handleKeep} onSwipeLeft={handleTrash} disabled={!currentImage}><ImageDisplay/></SwipeContainer><ThumbnailStrip/></>):(<div className="flex-1 flex items-center justify-center"><div className="text-center"><h2 className="text-lg font-medium text-muted-foreground">Workstation</h2><p className="text-sm text-muted-foreground/60 mt-1">Image review and curation</p></div></div>)}</div>)}
