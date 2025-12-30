//ThinkingSteps component - displays agent reasoning steps
import { useState } from 'react'
import { ChevronRight, ChevronDown, CheckCircle2, Loader2 } from 'lucide-react'
import type { ThinkingStep } from '@/lib/bridge'
interface Props {steps: ThinkingStep[];isGenerating: boolean;skills?: string[]}
export function ThinkingSteps({ steps, isGenerating, skills }: Props) {
  //Show spinner placeholder if generating but no steps yet
  if (steps.length === 0) {
    if (!isGenerating) return null
    return (<div className="flex items-center gap-2 text-sm text-muted-foreground py-2"><Loader2 className="h-4 w-4 animate-spin" /><span>Processing...</span></div>)
  }
  return (
    <div className="space-y-1 py-2">
      {skills && skills.length > 0 && (<div className="flex flex-wrap gap-1.5 mb-2 overflow-x-auto">{skills.slice(0,5).map((sk) => (<span key={sk} className="text-[9px] uppercase tracking-wider text-muted-foreground border border-border/40 px-1.5 py-0.5 rounded-sm whitespace-nowrap">{sk.length > 25 ? sk.slice(0,22) + '...' : sk}</span>))}{skills.length > 5 && (<span className="text-[9px] text-muted-foreground">+{skills.length - 5} more</span>)}</div>)}
      {steps.map((s) => (<StepItem key={s.id} step={s} />))}
      {isGenerating && (<div className="flex items-center gap-2 text-sm text-muted-foreground"><Loader2 className="h-3 w-3 animate-spin" /><span>Working...</span></div>)}
    </div>
  )
}
function StepItem({ step }: { step: ThinkingStep }) {
  const [exp, setExp] = useState(false)
  return (
    <div className="text-sm">
      <button type="button" onClick={() => setExp(!exp)} className="flex items-center gap-2 w-full text-left hover:bg-muted/50 rounded px-1 py-0.5 transition-colors">
        <CheckCircle2 className="h-3 w-3 text-green-500 flex-shrink-0" />
        <span className="font-medium text-foreground">{step.step}</span>
        {step.detail && (exp ? <ChevronDown className="h-3 w-3 text-muted-foreground ml-auto" /> : <ChevronRight className="h-3 w-3 text-muted-foreground ml-auto" />)}
      </button>
      {exp && step.detail && (<div className="pl-6 pr-2 py-1 text-muted-foreground text-xs">{step.detail}</div>)}
    </div>
  )
}
