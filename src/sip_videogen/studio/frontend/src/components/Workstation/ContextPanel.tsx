//ContextPanel - shows image metadata (prompt, source, timestamp)
import{useState,useCallback}from'react'
import{useWorkstation}from'../../context/WorkstationContext'
import{Button}from'../ui/button'
interface ContextPanelProps{className?:string}
export function ContextPanel({className=''}:ContextPanelProps){
const{currentBatch,selectedIndex}=useWorkstation()
const[expanded,setExpanded]=useState(false)
const currentImage=currentBatch[selectedIndex]
const toggle=useCallback(()=>setExpanded(e=>!e),[])
const copyPrompt=useCallback(async()=>{if(!currentImage?.prompt)return;try{await navigator.clipboard.writeText(currentImage.prompt)}catch(e){console.error('Failed to copy prompt:',e)}},[currentImage?.prompt])
if(!currentImage)return null
const ts=currentImage.timestamp?new Date(currentImage.timestamp).toLocaleString():null
const src=currentImage.sourceTemplatePath?.split('/').pop()
return(<div className={`absolute top-2 right-2 z-10 ${className}`}>{expanded?(<div className="bg-background/95 backdrop-blur-sm border border-border rounded-lg shadow-lg p-3 min-w-[220px] max-w-[320px]"><div className="flex items-center justify-between mb-2"><span className="text-xs font-medium text-muted-foreground">Image Details</span><Button variant="ghost" size="sm" className="h-6 w-6 p-0" onClick={toggle}><svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12"/></svg></Button></div>{currentImage.prompt?(<div className="mb-3"><div className="flex items-center justify-between mb-1"><span className="text-xs text-muted-foreground">Prompt</span><Button variant="ghost" size="sm" className="h-5 px-1.5 text-xs" onClick={copyPrompt}><svg className="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"/></svg>Copy</Button></div><p className="text-xs text-foreground/90 line-clamp-4">{currentImage.prompt}</p></div>):(<p className="text-xs text-muted-foreground mb-3">No prompt available</p>)}{src&&(<div className="mb-2"><span className="text-xs text-muted-foreground block mb-0.5">Source Template</span><span className="text-xs text-foreground/90">{src}</span></div>)}{ts&&(<div><span className="text-xs text-muted-foreground block mb-0.5">Generated</span><span className="text-xs text-foreground/90">{ts}</span></div>)}</div>):(<Button variant="ghost" size="sm" className="h-8 w-8 p-0 bg-background/80 backdrop-blur-sm border border-border/50 shadow-sm" onClick={toggle}><svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg></Button>)}</div>)}
