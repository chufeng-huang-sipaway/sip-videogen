//Playground mode for quick image generation (image-only, no video support)
import { useState, useEffect, useRef } from 'react'
import { Zap, AlertCircle, X } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { AspectRatioSelector } from '@/components/ChatPanel/AspectRatioSelector'
import { CapsuleSelector } from './CapsuleSelector'
import { PreviewCanvas } from './PreviewCanvas'
import { bridge } from '@/lib/bridge'
import { useProducts } from '@/context/ProductContext'
import { useStyleReferences } from '@/context/StyleReferenceContext'
import { useWorkstation } from '@/context/WorkstationContext'
import { type AspectRatio, isValidAspectRatio } from '@/types/aspectRatio'
//LocalStorage helpers with safety
const STORAGE_KEY = 'playground-aspect-ratio'
function getStoredAspectRatio(): AspectRatio { try { const v = localStorage.getItem(STORAGE_KEY); return v && isValidAspectRatio(v) ? v : '1:1' } catch { return '1:1' } }
function setStoredAspectRatio(v: AspectRatio): void { try { localStorage.setItem(STORAGE_KEY, v) } catch {/*ignore*/ } }
interface PlaygroundModeProps { brandSlug: string | null }
export function PlaygroundMode({ brandSlug }: PlaygroundModeProps) {
    const [prompt, setPrompt] = useState('')
    const [selectedProduct, setSelectedProduct] = useState('')
    const [selectedStyleRef, setSelectedStyleRef] = useState('')
    const [aspectRatio, setAspectRatio] = useState<AspectRatio>(getStoredAspectRatio)
    const [isGenerating, setIsGenerating] = useState(false)
    const [isStopped, setIsStopped] = useState(false)
    const [result, setResult] = useState<{ path: string; data?: string } | null>(null)
    const [error, setError] = useState<string | null>(null)
    const abortRef = useRef(false)
    //Brand-aware hooks for products/styles
    const { products } = useProducts()
    const { styleReferences } = useStyleReferences()
    const { bumpStatusVersion } = useWorkstation()
    //Reset selections when brandSlug changes
    useEffect(() => { setSelectedProduct(''); setSelectedStyleRef('') }, [brandSlug])
    //Persist aspect ratio
    useEffect(() => { setStoredAspectRatio(aspectRatio) }, [aspectRatio])
    const handleGenerate = async () => {
        if (!prompt.trim()) return
        abortRef.current = false; setIsStopped(false)
        setIsGenerating(true); setError(null); setResult(null)
        try {
            const res = await bridge.quickGenerate(prompt, selectedProduct || undefined, selectedStyleRef || undefined, aspectRatio, 1)
            if (abortRef.current) { setIsGenerating(false); return }
            if (res.images?.[0]) { setResult(res.images[0]); bumpStatusVersion() }
            else if (res.error) setError(res.error)
            else if (res.errors?.[0]) setError(res.errors[0].error)
        } catch (e) { if (!abortRef.current) setError(e instanceof Error ? e.message : String(e)) }
        finally { setIsGenerating(false) }
    }
    const handleStop = () => { abortRef.current = true; setIsStopped(true); setIsGenerating(false) }
    const handleClearPrompt = () => { setPrompt('') }
    //Map products/styles for CapsuleSelector
    const productItems = products.map(p => ({ slug: p.slug, name: p.name, description: p.description, imagePath: p.primary_image }))
    const styleItems = styleReferences.map(s => ({ slug: s.slug, name: s.name, description: s.description, imagePath: s.primary_image }))
    //No brand selected state
    if (!brandSlug) return (<div className="flex flex-col items-center justify-center h-full text-center p-8"><div className="text-muted-foreground text-sm">Select a brand to use Playground</div></div>)
    return (
        <div className="flex flex-col h-full bg-neutral-50/50 dark:bg-neutral-900/20">
            <div className="flex-1 flex flex-col items-center justify-center overflow-hidden max-w-3xl mx-auto w-full">
                <PreviewCanvas
                    aspectRatio={aspectRatio}
                    isLoading={isGenerating}
                    result={result}
                    onStop={handleStop}
                    showSaved={!!result && !isGenerating}
                />
            </div>

            {error && (
                <div className="px-6 pb-2 max-w-3xl mx-auto w-full">
                    <Alert variant="destructive" className="rounded-xl shadow-sm">
                        <AlertCircle className="h-4 w-4" />
                        <AlertDescription>{error}</AlertDescription>
                    </Alert>
                </div>
            )}
            {isStopped && !error && (
                <div className="px-6 pb-2 max-w-3xl mx-auto w-full">
                    <Alert className="rounded-xl shadow-sm bg-muted/50 border-muted">
                        <AlertDescription className="text-muted-foreground text-xs font-medium">
                            Generation stopped
                        </AlertDescription>
                    </Alert>
                </div>
            )}

            {/* Floating Command Center Input */}
            <div className="px-6 pb-6 pt-2 w-full max-w-3xl mx-auto z-20">
                <div
                    className={cn(
                        "relative flex flex-col rounded-3xl bg-background/80 backdrop-blur-md shadow-lg border border-white/20 transition-all duration-300",
                        "focus-within:shadow-[0_8px_30px_rgba(0,0,0,0.12)] focus-within:bg-background focus-within:border-white/40",
                        "dark:bg-neutral-900/80 dark:border-white/10 dark:focus-within:bg-neutral-900 dark:focus-within:border-white/20"
                    )}
                >
                    {/* Textarea Area */}
                    <div className="relative px-1">
                        <textarea
                            value={prompt}
                            onChange={(e) => setPrompt(e.target.value)}
                            placeholder="What are we creating today..."
                            rows={1}
                            disabled={isGenerating}
                            className="w-full px-4 py-4 pr-10 resize-none text-sm bg-transparent border-0 focus:outline-none focus:ring-0 disabled:opacity-50 disabled:cursor-not-allowed placeholder:text-muted-foreground/50 leading-relaxed min-h-[56px]"
                            style={{ minHeight: "56px" }}
                        />
                        {prompt && !isGenerating && (
                            <button
                                type="button"
                                onClick={handleClearPrompt}
                                className="absolute right-4 top-4 p-1 rounded-full hover:bg-muted/80 text-muted-foreground transition-colors"
                                title="Clear prompt"
                            >
                                <X className="w-3.5 h-3.5" strokeWidth={2} />
                            </button>
                        )}
                    </div>

                    {/* Bottom Control Bar */}
                    <div className="flex items-center justify-between px-2 pb-2 mt-[-4px]">
                        {/* Left: Inputs */}
                        <div className="flex items-center gap-2 pl-1">
                            <CapsuleSelector
                                items={productItems}
                                value={selectedProduct}
                                onChange={setSelectedProduct}
                                disabled={isGenerating}
                                placeholder="Product"
                                emptyLabel="No product"
                                type="product"
                            />
                            <CapsuleSelector
                                items={styleItems}
                                value={selectedStyleRef}
                                onChange={setSelectedStyleRef}
                                disabled={isGenerating}
                                placeholder="Style"
                                emptyLabel="No style"
                                type="style"
                            />
                        </div>

                        {/* Right: Actions */}
                        <div className="flex items-center gap-2 pr-1">
                            <div className="h-8 flex items-center bg-muted/30 rounded-full px-1 border border-border/20">
                                <AspectRatioSelector
                                    value={aspectRatio}
                                    onChange={setAspectRatio}
                                    generationMode="image"
                                    disabled={isGenerating}
                                />
                            </div>

                            <Button
                                onClick={handleGenerate}
                                disabled={!prompt.trim() || isGenerating}
                                size="icon"
                                className={cn(
                                    "h-9 w-9 rounded-full shrink-0 transition-all duration-300",
                                    "bg-brand-500 text-white hover:bg-brand-600 active:scale-95",
                                    "shadow-[0_0_20px_rgba(237,9,66,0.3)] hover:shadow-[0_0_25px_rgba(237,9,66,0.5)]",
                                    "disabled:opacity-20 disabled:bg-muted disabled:text-muted-foreground disabled:shadow-none"
                                )}
                            >
                                <Zap className="h-4 w-4 fill-current" strokeWidth={1.5} />
                            </Button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    )
}
