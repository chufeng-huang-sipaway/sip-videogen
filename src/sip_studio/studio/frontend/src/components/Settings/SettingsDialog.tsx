
import { useState, useEffect } from 'react'
import { Dialog, DialogContent, DialogTitle } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Eye, EyeOff, Globe, Sparkles, ShieldCheck, ShieldAlert, X } from 'lucide-react'
import { Spinner } from '@/components/ui/spinner'
import { bridge, isPyWebView } from '@/lib/bridge'
import { cn } from '@/lib/utils'

interface Props {
  open: boolean
  onOpenChange: (open: boolean) => void
}

interface KeyStatus {
  openai: boolean
  gemini: boolean
  firecrawl: boolean
  all_configured: boolean
}

export function SettingsDialog({ open, onOpenChange }: Props) {
  const [status, setStatus] = useState<KeyStatus | null>(null)

  // Form State
  const [openaiKey, setOpenaiKey] = useState('')
  const [geminiKey, setGeminiKey] = useState('')
  const [firecrawlKey, setFirecrawlKey] = useState('')
  const [showKeys, setShowKeys] = useState(false)
  const [saving, setSaving] = useState(false)

  // Feedback State
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)

  useEffect(() => {
    if (open && isPyWebView()) {
      bridge.checkApiKeys().then(s => setStatus(s)).catch(() => { })
      // Reset form state on open
      setOpenaiKey('')
      setGeminiKey('')
      setFirecrawlKey('')
      setError(null)
      setSuccess(false)
    }
  }, [open])

  const onSave = async () => {
    setError(null)
    setSuccess(false)
    setSaving(true)

    try {
      if (isPyWebView()) {
        await bridge.saveApiKeys(
          openaiKey || '__KEEP__',
          geminiKey || '__KEEP__',
          firecrawlKey
        )
        // Refresh status
        const newStatus = await bridge.checkApiKeys()
        setStatus(newStatus)
        setSuccess(true)

        // Clear inputs
        setOpenaiKey('')
        setGeminiKey('')
        setFirecrawlKey('')

        // Close after brief success (optional, keeping open for feedback)
        setTimeout(() => setSuccess(false), 3000)
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to save settings')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md p-0 overflow-hidden bg-background/95 backdrop-blur-2xl border border-white/20 shadow-2xl rounded-[32px] ring-1 ring-black/5 [&>button]:hidden">
        <div className="sr-only">
          <DialogTitle>Settings</DialogTitle>
        </div>

        {/* Header */}
        <div className="px-8 pt-8 pb-6 flex items-start justify-between">
          <div>
            <h2 className="text-xl font-semibold tracking-tight text-foreground">Settings</h2>
            <p className="text-sm text-muted-foreground/60 font-medium">Manage your API connections</p>
          </div>
          <div className="flex items-center gap-1">
            <button onClick={() => setShowKeys(!showKeys)} className="h-9 px-3 rounded-full hover:bg-secondary/50 flex items-center gap-1.5 transition-colors text-xs font-medium text-muted-foreground hover:text-foreground">
              {showKeys?<EyeOff className="w-3.5 h-3.5"/>:<Eye className="w-3.5 h-3.5"/>}
              {showKeys?'Hide':'Show'}
            </button>
            <button onClick={() => onOpenChange(false)} className="h-9 w-9 rounded-full hover:bg-secondary/50 flex items-center justify-center transition-colors">
              <X className="h-4 w-4 text-muted-foreground" strokeWidth={1.5} />
            </button>
          </div>
        </div>

        <div className="px-8 pb-8 space-y-6">
          {/* Unified Card with All Fields */}
          <div className="rounded-2xl border border-border/10 bg-secondary/20 overflow-hidden divide-y divide-border/10">
            <ApiKeyRow label="OpenAI" icon={<Sparkles className="w-4 h-4"/>} configured={status?.openai??false} value={openaiKey} onChange={setOpenaiKey} placeholder={status?.openai?"••••••••••••••••":"sk-..."} show={showKeys}/>
            <ApiKeyRow label="Gemini" icon={<Sparkles className="w-4 h-4"/>} configured={status?.gemini??false} value={geminiKey} onChange={setGeminiKey} placeholder={status?.gemini?"••••••••••••••••":"AI..."} show={showKeys}/>
            <ApiKeyRow label="FireCrawl" hint="Optional" icon={<Globe className="w-4 h-4"/>} configured={status?.firecrawl??false} value={firecrawlKey} onChange={setFirecrawlKey} placeholder={status?.firecrawl?"••••••••••••••••":"fc-..."} show={showKeys}/>
          </div>

          {/* Notifications */}
          <div className="min-h-[20px]">
            {error&&(<div className="flex items-center gap-2 text-destructive text-xs animate-in slide-in-from-left-2 fade-in"><ShieldAlert className="w-3.5 h-3.5"/><span>{error}</span></div>)}
            {success&&(<div className="flex items-center gap-2 text-success text-xs animate-in slide-in-from-left-2 fade-in"><ShieldCheck className="w-3.5 h-3.5"/><span>Credentials updated successfully</span></div>)}
          </div>

          <Button onClick={onSave} disabled={saving||(!openaiKey&&!geminiKey&&!firecrawlKey)} className="w-full h-11 rounded-full font-medium transition-all shadow-lg hover:shadow-xl active:scale-[0.98]">
            {saving?(<span className="flex items-center gap-2"><Spinner className="h-4 w-4"/>Saving...</span>):('Save Changes')}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}

//Compact row inside unified card
function ApiKeyRow({label,hint,icon,configured,value,onChange,placeholder,show}:{label:string;hint?:string;icon:React.ReactNode;configured:boolean;value:string;onChange:(v:string)=>void;placeholder:string;show:boolean}){
  return(
    <div className="px-4 py-4 space-y-3">
      <div className="flex items-center gap-3">
        <div className={cn("h-9 w-9 rounded-xl flex items-center justify-center",configured?"bg-background text-foreground shadow-sm":"bg-muted/30 text-muted-foreground")}>{icon}</div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-foreground">{label}</span>
            {hint&&<span className="text-[10px] text-muted-foreground/60">{hint}</span>}
          </div>
        </div>
        <div className={cn("flex items-center gap-1.5 text-[11px] font-medium",configured?"text-success":"text-muted-foreground/50")}>
          <div className={cn("w-1.5 h-1.5 rounded-full",configured?"bg-success":"bg-muted-foreground/30")}/>
          {configured?"Active":"Not Set"}
        </div>
      </div>
      <Input type={show?"text":"password"} value={value} onChange={(e)=>onChange(e.target.value)} placeholder={placeholder} className="h-10 px-3 rounded-xl border-0 bg-background/60 hover:bg-background focus:bg-background focus:ring-1 focus:ring-ring transition-all text-sm placeholder:text-muted-foreground/30"/>
    </div>
  )
}
