//ExportActions component - copy, reveal in finder, and drag-out functionality
import{useCallback,useState,useRef}from'react'
import{useWorkstation}from'../../context/WorkstationContext'
import{bridge}from'../../lib/bridge'
import{Button}from'../ui/button'
interface ExportActionsProps{className?:string}
export function ExportActions({className=''}:ExportActionsProps){
const{currentBatch,selectedIndex}=useWorkstation()
const currentImage=currentBatch[selectedIndex]
const[copying,setCopying]=useState(false)
const[copied,setCopied]=useState(false)
const dragRef=useRef<HTMLDivElement>(null)
//Copy image to clipboard
const handleCopy=useCallback(async()=>{if(!currentImage)return;setCopying(true);setCopied(false);try{await bridge.copyImageToClipboard(currentImage.originalPath||currentImage.path);setCopied(true);setTimeout(()=>setCopied(false),2000)}catch(e){console.error('Failed to copy:',e)}finally{setCopying(false)}},[currentImage])
//Reveal in Finder
const handleReveal=useCallback(async()=>{if(!currentImage)return;try{await bridge.shareImage(currentImage.originalPath||currentImage.path)}catch(e){console.error('Failed to reveal:',e)}},[currentImage])
//Handle drag start for drag-out
const handleDragStart=useCallback((e:React.DragEvent)=>{if(!currentImage)return;const p=currentImage.originalPath||currentImage.path;e.dataTransfer.effectAllowed='copy';e.dataTransfer.setData('text/uri-list',`file://${p}`);e.dataTransfer.setData('text/plain',p)},[currentImage])
//Context menu handler
const handleContextMenu=useCallback((e:React.MouseEvent)=>{e.preventDefault();if(!currentImage)return},[currentImage])
if(!currentImage)return null
return(<div className={`flex items-center gap-1 ${className}`} ref={dragRef} draggable onDragStart={handleDragStart} onContextMenu={handleContextMenu}>{/* Copy button */}<Button variant="ghost" size="icon" className="h-8 w-8" onClick={handleCopy} disabled={copying} title="Copy to clipboard">{copying?(<svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"/></svg>):copied?(<svg className="w-4 h-4 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7"/></svg>):(<svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"/></svg>)}</Button>{/* Reveal in Finder button */}<Button variant="ghost" size="icon" className="h-8 w-8" onClick={handleReveal} title="Reveal in Finder"><svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"/></svg></Button>{/* Drag indicator */}<div className="h-8 w-8 flex items-center justify-center text-muted-foreground cursor-grab" title="Drag to export"><svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16V4m0 0L3 8m4-4l4 4m6 0v12m0 0l4-4m-4 4l-4-4"/></svg></div></div>)}
