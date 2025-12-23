import { useState, useEffect } from 'react'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Check, X, Eye, EyeOff, AlertCircle } from 'lucide-react'
import { bridge, isPyWebView } from '@/lib/bridge'
interface Props {open:boolean;onOpenChange:(open:boolean)=>void}
interface KeyStatus {openai:boolean;gemini:boolean;firecrawl:boolean;all_configured:boolean}
export function SettingsDialog({open,onOpenChange}:Props) {
  const [status,setStatus]=useState<KeyStatus|null>(null)
  const [openaiKey,setOpenaiKey]=useState('')
  const [geminiKey,setGeminiKey]=useState('')
  const [firecrawlKey,setFirecrawlKey]=useState('')
  const [showKeys,setShowKeys]=useState(false)
  const [saving,setSaving]=useState(false)
  const [error,setError]=useState<string|null>(null)
  const [success,setSuccess]=useState(false)
  useEffect(()=>{
    if(open&&isPyWebView()){
      bridge.checkApiKeys().then(s=>setStatus(s)).catch(()=>{})
      //Reset form state
      setOpenaiKey('');setGeminiKey('');setFirecrawlKey('')
      setError(null);setSuccess(false)
    }
  },[open])
  const onSave=async()=>{
    setError(null);setSuccess(false);setSaving(true)
    try{
      if(isPyWebView()){
        await bridge.saveApiKeys(openaiKey||'__KEEP__',geminiKey||'__KEEP__',firecrawlKey)
        const newStatus=await bridge.checkApiKeys()
        setStatus(newStatus)
        setSuccess(true)
        setOpenaiKey('');setGeminiKey('');setFirecrawlKey('')
      }
    }catch(e){setError(e instanceof Error?e.message:'Failed to save')}
    finally{setSaving(false)}
  }
  const KeyStatusBadge=({configured,label}:{configured:boolean;label:string})=>(
    <div className="flex items-center justify-between py-2 px-3 rounded-lg bg-muted/50">
      <span className="text-sm">{label}</span>
      {configured?(<span className="flex items-center gap-1 text-xs text-green-600"><Check className="w-3 h-3"/>Configured</span>)
      :(<span className="flex items-center gap-1 text-xs text-amber-600"><X className="w-3 h-3"/>Not set</span>)}
    </div>
  )
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader><DialogTitle>Settings</DialogTitle></DialogHeader>
        <div className="space-y-4">
          {/* Current Status */}
          <div className="space-y-2">
            <h4 className="text-sm font-medium text-muted-foreground">API Key Status</h4>
            {status&&(<div className="space-y-1">
              <KeyStatusBadge configured={status.openai} label="OpenAI"/>
              <KeyStatusBadge configured={status.gemini} label="Gemini"/>
              <KeyStatusBadge configured={status.firecrawl} label="FireCrawl (URL reading)"/>
            </div>)}
          </div>
          {/* Update Keys */}
          <div className="space-y-3 pt-2 border-t">
            <div className="flex items-center justify-between">
              <h4 className="text-sm font-medium">Update API Keys</h4>
              <Button variant="ghost" size="sm" className="h-7 gap-1" onClick={()=>setShowKeys(!showKeys)}>
                {showKeys?<EyeOff className="w-3 h-3"/>:<Eye className="w-3 h-3"/>}
                <span className="text-xs">{showKeys?'Hide':'Show'}</span>
              </Button>
            </div>
            <p className="text-xs text-muted-foreground">Leave empty to keep current value</p>
            <div className="space-y-2">
              <div>
                <label className="text-xs text-muted-foreground">OpenAI API Key</label>
                <Input type={showKeys?"text":"password"} placeholder={status?.openai?"••••••••••••":"sk-..."} value={openaiKey} onChange={e=>setOpenaiKey(e.target.value)} className="h-8 text-sm"/>
              </div>
              <div>
                <label className="text-xs text-muted-foreground">Gemini API Key</label>
                <Input type={showKeys?"text":"password"} placeholder={status?.gemini?"••••••••••••":"AI..."} value={geminiKey} onChange={e=>setGeminiKey(e.target.value)} className="h-8 text-sm"/>
              </div>
              <div>
                <label className="text-xs text-muted-foreground">FireCrawl API Key <span className="text-gray-400">(optional)</span></label>
                <Input type={showKeys?"text":"password"} placeholder={status?.firecrawl?"••••••••••••":"fc-..."} value={firecrawlKey} onChange={e=>setFirecrawlKey(e.target.value)} className="h-8 text-sm"/>
                <p className="text-[10px] text-muted-foreground mt-1">Enables reading URLs shared in chat</p>
              </div>
            </div>
            {error&&(<Alert variant="destructive" className="py-2"><AlertCircle className="h-3 w-3"/><AlertDescription className="text-xs">{error}</AlertDescription></Alert>)}
            {success&&(<Alert className="py-2 border-green-200 bg-green-50 dark:bg-green-950/20"><Check className="h-3 w-3 text-green-600"/><AlertDescription className="text-xs text-green-600">API keys updated successfully</AlertDescription></Alert>)}
            <Button onClick={onSave} disabled={saving||(!openaiKey&&!geminiKey&&!firecrawlKey)} className="w-full h-8">
              {saving?'Saving...':'Save Changes'}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
