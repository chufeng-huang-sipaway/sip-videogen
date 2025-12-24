
import { useState, useEffect } from 'react'
import { Dialog, DialogContent, DialogTitle } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Eye, EyeOff, Loader2, Key, Globe, Sparkles, ShieldCheck, ShieldAlert, X } from 'lucide-react'
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

        {/* Minimal Header */}
        <div className="px-8 pt-8 pb-4 flex items-center justify-between relative">
          <div>
            <h2 className="text-xl font-semibold tracking-tight text-foreground">Settings</h2>
            <p className="text-sm text-muted-foreground/60 font-medium">Manage your API connections</p>
          </div>
          <div className="flex gap-2">
            <div className="h-10 w-10 rounded-full bg-secondary/50 flex items-center justify-center">
              <Key className="h-5 w-5 text-foreground/40" strokeWidth={1.5} />
            </div>
            <button onClick={() => onOpenChange(false)} className="h-10 w-10 rounded-full hover:bg-secondary/50 flex items-center justify-center transition-colors">
              <X className="h-5 w-5 text-foreground/40" strokeWidth={1.5} />
            </button>
          </div>
        </div>

        <div className="px-8 pb-8 space-y-8">

          {/* Status Section */}
          <div className="space-y-4">
            <h3 className="text-[10px] uppercase tracking-widest text-muted-foreground/50 font-semibold pl-1">Connection Status</h3>
            <div className="grid gap-3">
              {status && (
                <>
                  <StatusRow
                    label="OpenAI"
                    configured={status.openai}
                    icon={<Sparkles className="w-3.5 h-3.5" />}
                  />
                  <StatusRow
                    label="Gemini"
                    configured={status.gemini}
                    icon={<Sparkles className="w-3.5 h-3.5" />}
                  />
                  <StatusRow
                    label="FireCrawl"
                    description="URL Reading"
                    configured={status.firecrawl}
                    icon={<Globe className="w-3.5 h-3.5" />}
                  />
                </>
              )}
            </div>
          </div>

          {/* Update Section */}
          <div className="space-y-4">
            <div className="flex items-center justify-between pl-1">
              <h3 className="text-[10px] uppercase tracking-widest text-muted-foreground/50 font-semibold">Update Credentials</h3>
              <button
                onClick={() => setShowKeys(!showKeys)}
                className="text-[10px] uppercase tracking-widest text-primary/70 hover:text-primary font-semibold flex items-center gap-1.5 transition-colors focus:outline-none"
              >
                {showKeys ? <EyeOff className="w-3 h-3" /> : <Eye className="w-3 h-3" />}
                {showKeys ? 'Hide' : 'Show'}
              </button>
            </div>

            <div className="space-y-3">
              <MinimalInput
                label="OpenAI API Key"
                value={openaiKey}
                onChange={setOpenaiKey}
                placeholder={status?.openai ? "••••••••••••••••" : "sk-..."}
                show={showKeys}
              />
              <MinimalInput
                label="Gemini API Key"
                value={geminiKey}
                onChange={setGeminiKey}
                placeholder={status?.gemini ? "••••••••••••••••" : "AI..."}
                show={showKeys}
              />
              <MinimalInput
                label="FireCrawl API Key (Optional)"
                value={firecrawlKey}
                onChange={setFirecrawlKey}
                placeholder={status?.firecrawl ? "••••••••••••••••" : "fc-..."}
                show={showKeys}
              />
            </div>

            {/* Notifications */}
            <div className="min-h-[20px]">
              {error && (
                <div className="flex items-center gap-2 text-destructive text-xs animate-in slide-in-from-left-2 fade-in">
                  <ShieldAlert className="w-3.5 h-3.5" />
                  <span>{error}</span>
                </div>
              )}
              {success && (
                <div className="flex items-center gap-2 text-green-600 text-xs animate-in slide-in-from-left-2 fade-in">
                  <ShieldCheck className="w-3.5 h-3.5" />
                  <span>Credentials updated successfully</span>
                </div>
              )}
            </div>

            <Button
              onClick={onSave}
              disabled={saving || (!openaiKey && !geminiKey && !firecrawlKey)}
              className={cn(
                "w-full h-11 rounded-full font-medium transition-all shadow-lg hover:shadow-xl active:scale-[0.98]",
                saving ? "bg-muted text-muted-foreground" : "bg-black text-white hover:bg-neutral-800 dark:bg-white dark:text-black dark:hover:bg-neutral-200"
              )}
            >
              {saving ? (
                <span className="flex items-center gap-2">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Saving...
                </span>
              ) : (
                'Save Changes'
              )}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}

function StatusRow({ label, description, configured, icon }: { label: string, description?: string, configured: boolean, icon: any }) {
  return (
    <div className="flex items-center justify-between p-3 rounded-2xl bg-secondary/30 border border-border/5">
      <div className="flex items-center gap-3">
        <div className={cn(
          "h-8 w-8 rounded-xl flex items-center justify-center shadow-sm",
          configured ? "bg-background text-foreground" : "bg-muted/50 text-muted-foreground"
        )}>
          {icon}
        </div>
        <div>
          <div className="text-sm font-medium text-foreground/90">{label}</div>
          {description && <div className="text-[10px] text-muted-foreground">{description}</div>}
        </div>
      </div>

      <div className={cn(
        "flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-medium border",
        configured
          ? "bg-green-500/10 text-green-700 border-green-500/20 dark:text-green-400"
          : "bg-muted text-muted-foreground border-transparent"
      )}>
        <div className={cn("w-1.5 h-1.5 rounded-full", configured ? "bg-green-500" : "bg-muted-foreground/40")} />
        {configured ? "Active" : "Not Set"}
      </div>
    </div>
  )
}

function MinimalInput({ label, value, onChange, placeholder, show }: any) {
  return (
    <div className="group relative">
      <div className="absolute left-4 top-3.5 text-[10px] uppercase tracking-wider font-semibold text-muted-foreground/40 pointer-events-none transition-all group-focus-within:text-primary/50">
        {label}
      </div>
      <Input
        type={show ? "text" : "password"}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="h-14 pt-6 pb-2 px-4 rounded-2xl border-border/10 bg-secondary/30 hover:bg-secondary/50 focus:bg-background focus:border-black/5 focus:shadow-sm focus:ring-1 focus:ring-black/5 transition-all text-sm font-medium placeholder:text-muted-foreground/20"
      />
    </div>
  )
}
