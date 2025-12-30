import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Key, AlertCircle } from 'lucide-react'
import { bridge, isPyWebView } from '@/lib/bridge'
interface ApiKeySetupProps {onComplete: () => void}
export function ApiKeySetup({ onComplete }: ApiKeySetupProps) {
  const [openaiKey, setOpenaiKey] = useState('')
  const [geminiKey, setGeminiKey] = useState('')
  const [firecrawlKey, setFirecrawlKey] = useState('')
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();setError(null)
    if (!openaiKey.trim() || !geminiKey.trim()) {setError('OpenAI and Gemini API keys are required.');return}
    setIsSaving(true)
    try {
      if (isPyWebView()) await bridge.saveApiKeys(openaiKey.trim(), geminiKey.trim(), firecrawlKey.trim())
      onComplete()
    } catch (err) {setError(err instanceof Error ? err.message : 'Failed to save keys')}
    finally {setIsSaving(false)}
  }
  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <div className="max-w-md w-full space-y-6">
        <div className="text-center">
          <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-brand-500 to-brand-600 flex items-center justify-center mx-auto mb-4">
            <Key className="h-8 w-8 text-white" />
          </div>
          <h1 className="text-2xl font-bold">Welcome to Brand Studio</h1>
          <p className="text-muted-foreground mt-2">Enter your API keys to get started</p>
        </div>
        {error && (<Alert variant="destructive"><AlertCircle className="h-4 w-4" /><AlertDescription>{error}</AlertDescription></Alert>)}
        <form onSubmit={onSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">OpenAI API Key <span className="text-destructive">*</span></label>
            <Input type="password" placeholder="sk-…" value={openaiKey} onChange={(e) => setOpenaiKey(e.target.value)} />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Gemini API Key <span className="text-destructive">*</span></label>
            <Input type="password" placeholder="AI…" value={geminiKey} onChange={(e) => setGeminiKey(e.target.value)} />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">FireCrawl API Key <span className="text-muted-foreground/60 text-xs">(optional)</span></label>
            <Input type="password" placeholder="fc-…" value={firecrawlKey} onChange={(e) => setFirecrawlKey(e.target.value)} />
            <p className="text-xs text-muted-foreground/60 mt-1">Enables reading URLs shared in chat</p>
          </div>
          <Button type="submit" className="w-full" disabled={isSaving}>{isSaving ? 'Saving…' : 'Get Started'}</Button>
        </form>
        <p className="text-xs text-center text-muted-foreground/60">Keys are saved locally in ~/.sip-videogen/config.json</p>
      </div>
    </div>
  )
}
