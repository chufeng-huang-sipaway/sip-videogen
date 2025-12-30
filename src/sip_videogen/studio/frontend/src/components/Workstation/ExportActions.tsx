//ExportActions component - copy and reveal in finder
import { useCallback, useState } from 'react'
import { useWorkstation } from '../../context/WorkstationContext'
import { bridge } from '../../lib/bridge'
import { Button } from '../ui/button'
import { Tooltip, TooltipContent, TooltipTrigger } from '../ui/tooltip'
import { cn } from '@/lib/utils'
interface ExportActionsProps { className?: string; variant?: 'light' | 'dark' }
export function ExportActions({ className = '', variant = 'light' }: ExportActionsProps) {
    const { currentBatch, selectedIndex } = useWorkstation()
    const currentImage = currentBatch[selectedIndex]
    const [copying, setCopying] = useState(false)
    const [copied, setCopied] = useState(false)
    const isDark = variant === 'dark'
    const btnClass = cn("h-9 w-9 rounded-full transition-all", isDark ? "text-white/90 hover:bg-white/10" : "hover:bg-black/5 dark:hover:bg-white/10")
    //Copy image to clipboard
    const handleCopy = useCallback(async () => { if (!currentImage) return; setCopying(true); setCopied(false); try { await bridge.copyImageToClipboard(currentImage.originalPath || currentImage.path); setCopied(true); setTimeout(() => setCopied(false), 2000) } catch (e) { console.error('Failed to copy:', e) } finally { setCopying(false) } }, [currentImage])
    //Reveal in Finder
    const handleReveal = useCallback(async () => { if (!currentImage) return; try { await bridge.shareImage(currentImage.originalPath || currentImage.path) } catch (e) { console.error('Failed to reveal:', e) } }, [currentImage])
    if (!currentImage) return null
    return (<div className={`flex items-center gap-1 ${className}`}><Tooltip><TooltipTrigger asChild><Button variant="ghost" size="icon" className={btnClass} onClick={handleCopy} disabled={copying}>{copying ? (<svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" /></svg>) : copied ? (<svg className="w-4 h-4 text-success" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" /></svg>) : (<svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" /></svg>)}</Button></TooltipTrigger><TooltipContent side="top">Copy (C)</TooltipContent></Tooltip><Tooltip><TooltipTrigger asChild><Button variant="ghost" size="icon" className={btnClass} onClick={handleReveal}><svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" /></svg></Button></TooltipTrigger><TooltipContent side="top">Reveal in Finder</TooltipContent></Tooltip></div>)
}
