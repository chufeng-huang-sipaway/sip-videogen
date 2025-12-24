//ExportActions component - copy, share, and drag-out functionality
import{useCallback,useState,useRef}from'react'
import{useWorkstation}from'../../context/WorkstationContext'
import{bridge}from'../../lib/bridge'
import{Button}from'../ui/button'
interface ExportActionsProps{className?:string}
export function ExportActions({className=''}:ExportActionsProps){
const{currentBatch,selectedIndex}=useWorkstation()
const currentImage=currentBatch[selectedIndex]
const[copying,setCopying]=useState(false)
const[sharing,setSharing]=useState(false)
const[copied,setCopied]=useState(false)
const dragRef=useRef<HTMLDivElement>(null)
//Copy image to clipboard
const handleCopy=useCallback(async()=>{if(!currentImage)return;setCopying(true);setCopied(false);try{await bridge.copyImageToClipboard(currentImage.path);setCopied(true);setTimeout(()=>setCopied(false),2000)}catch(e){console.error('Failed to copy:',e)}finally{setCopying(false)}},[currentImage])
//Open macOS share sheet
const handleShare=useCallback(async()=>{if(!currentImage)return;setSharing(true);try{await bridge.shareImage(currentImage.path)}catch(e){console.error('Failed to share:',e)}finally{setSharing(false)}},[currentImage])
//Handle drag start for drag-out
const handleDragStart=useCallback((e:React.DragEvent)=>{if(!currentImage)return;e.dataTransfer.effectAllowed='copy';e.dataTransfer.setData('text/uri-list',`file://${currentImage.path}`);e.dataTransfer.setData('text/plain',currentImage.path)},[currentImage])
//Context menu handler
const handleContextMenu=useCallback((e:React.MouseEvent)=>{e.preventDefault();if(!currentImage)return},[currentImage])
if(!currentImage)return null
return(<div className={`flex items-center gap-1 ${className}`} ref={dragRef} draggable onDragStart={handleDragStart} onContextMenu={handleContextMenu}>{/* Copy button */}<Button variant="ghost" size="icon" className="h-8 w-8" onClick={handleCopy} disabled={copying} title="Copy to clipboard">{copying?(<svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"/></svg>):copied?(<svg className="w-4 h-4 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7"/></svg>):(<svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"/></svg>)}</Button>{/* Share button */}<Button variant="ghost" size="icon" className="h-8 w-8" onClick={handleShare} disabled={sharing} title="Share"><svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z"/></svg></Button>{/* Drag indicator */}<div className="h-8 w-8 flex items-center justify-center text-muted-foreground cursor-grab" title="Drag to export"><svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16V4m0 0L3 8m4-4l4 4m6 0v12m0 0l4-4m-4 4l-4-4"/></svg></div></div>)}
