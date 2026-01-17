import { useEffect, useRef, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { bridge, type ClarificationResponse } from '@/lib/bridge'
import type { Interaction, DeepResearchClarification } from '@/lib/bridge'
import { cn } from '@/lib/utils'
import { Telescope } from 'lucide-react'
interface Props { interaction: Interaction; onSelect: (selection: string) => void; disabled?: boolean }
export function InteractionRenderer({ interaction, onSelect, disabled }: Props) {
  const [cv, setCv] = useState('')
  const [imgPrev, setImgPrev] = useState<Record<string, string>>({})
  const reqPrev = useRef<Set<string>>(new Set())
  useEffect(() => { if (interaction.type !== 'image_select') return; for (const p of interaction.image_paths) { if (reqPrev.current.has(p)) continue; reqPrev.current.add(p); bridge.getAssetThumbnail(p).then((d) => { setImgPrev(pr => (pr[p] ? pr : { ...pr, [p]: d })) }).catch((e) => { reqPrev.current.delete(p); console.error('Failed to load preview:', e) }) } }, [interaction])
  if (interaction.type === 'choices') {
    return (
      <div className="mt-4 w-full">
        <div className="rounded-xl border border-border bg-card p-4 space-y-3 shadow-sm">
          <p className="text-sm text-foreground leading-relaxed">{interaction.question}</p>
          <div className="flex flex-col gap-2">
            {interaction.choices.map((c, i) => (<Button key={c} variant={i === 0 ? "default" : "outline"} size="sm" onClick={() => onSelect(c)} disabled={disabled} className={cn("w-full justify-start text-left whitespace-normal h-auto py-2.5 px-4", i === 0 && "font-medium")}>{c}</Button>))}
          </div>
          {interaction.allow_custom && (<div className="flex gap-2 pt-1">
            <Input placeholder="Or type something else..." value={cv} onChange={(e) => setCv(e.target.value)} disabled={disabled} className="text-sm" onKeyDown={(e) => { if (e.key === 'Enter' && cv.trim()) onSelect(cv) }} />
            <Button size="sm" onClick={() => onSelect(cv)} disabled={disabled || !cv.trim()}>Send</Button>
          </div>)}
        </div>
      </div>)
  }
  if (interaction.type === 'image_select') {
    return (
      <div className="mt-4 w-full">
        <div className="rounded-xl border border-border bg-card p-4 space-y-3 shadow-sm">
          <p className="text-sm text-foreground leading-relaxed">{interaction.question}</p>
          <div className="grid grid-cols-2 gap-2">
            {interaction.image_paths.map((p, i) => (<button key={p} onClick={() => onSelect(`Option ${i + 1}: ${interaction.labels[i]}`)} disabled={disabled} className="relative group border border-border rounded-lg overflow-hidden hover:ring-2 hover:ring-primary/50 hover:border-primary/50 disabled:opacity-50 text-left transition-all">
              {imgPrev[p] ? (<img src={imgPrev[p]} alt={interaction.labels[i]} className="w-full h-32 object-cover" />) : (<div className="w-full h-32 bg-muted flex items-center justify-center"><span className="text-muted-foreground text-xs">Loading...</span></div>)}
              <div className="absolute bottom-0 left-0 right-0 bg-black/70 text-white text-xs py-1.5 px-2">{interaction.labels[i]}</div>
            </button>))}
          </div>
        </div>
      </div>)
  }
  if (interaction.type === 'deep_research_clarification') {
    return (<ClarificationPanel interaction={interaction} onSubmit={(resp) => {
      bridge.executeDeepResearch(resp, interaction.query).then(r => { onSelect(`__research_started__:${r.response_id}:${interaction.query}`) }).catch(e => onSelect(`__research_error__:${e.message}`))
    }} onCancel={() => onSelect('__cancelled__')} disabled={disabled} />)
  }
  return null
}
function ClarificationPanel({ interaction, onSubmit, onCancel, disabled }: { interaction: DeepResearchClarification; onSubmit: (response: ClarificationResponse) => void; onCancel: () => void; disabled?: boolean }) {
  const [answers, setAnswers] = useState<Record<string, string>>({})
  const [submitting, setSubmitting] = useState(false)

  // Set default selection to the first option if not set, or recommended
  useEffect(() => {
    const newAnswers = { ...answers }
    let changed = false
    interaction.questions.forEach(q => {
      if (!newAnswers[q.id]) {
        const recommended = q.options.find(o => o.recommended)
        // Default to first option if no recommended one, to ensure smooth UX
        newAnswers[q.id] = recommended ? recommended.value : q.options[0]?.value
        changed = true
      }
    })
    if (changed) setAnswers(newAnswers)
  }, [interaction.questions])

  const handleSubmit = () => { if (submitting) return; setSubmitting(true); onSubmit({ answers, confirmed: true }) }
  const allAnswered = interaction.questions.every(q => answers[q.id] && answers[q.id].trim().length > 0)

  return (
    <div className="mt-6 w-full max-w-lg mx-auto animate-fade-in-up">
      <div className="glass-panel rounded-2xl p-6 space-y-6 shadow-float relative overflow-hidden">
        {/* Subtle top brand accent */}
        <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-brand-500/20 via-brand-500/40 to-brand-500/20" />

        {/* Header */}
        <div className="flex items-start gap-4">
          <div className="flex-shrink-0 w-10 h-10 rounded-full bg-brand-500/10 flex items-center justify-center text-brand-500">
            <Telescope className="h-5 w-5" />
          </div>
          <div className="space-y-1">
            <h3 className="text-base font-semibold leading-none pt-1">Deep Research</h3>
            <p className="text-sm text-muted-foreground">A few questions before I begin.</p>
          </div>
        </div>

        {/* Questions */}
        <div className="space-y-6">
          {interaction.questions.map(q => (
            <div key={q.id} className="space-y-3">
              <p className="text-sm font-medium text-foreground px-1">{q.question}</p>
              <div className="flex flex-col gap-2">
                {q.options.map(opt => {
                  const isSelected = answers[q.id] === opt.value;
                  return (
                    <button
                      key={opt.value}
                      onClick={() => setAnswers(a => ({ ...a, [q.id]: opt.value }))}
                      disabled={disabled || submitting}
                      className={cn(
                        "relative flex items-center w-full px-4 py-3 text-left transition-all duration-200 rounded-xl border border-transparent",
                        isSelected
                          ? "bg-brand-500/5 border-brand-500/20 shadow-sm"
                          : "bg-secondary/50 hover:bg-secondary border-border/50 hover:border-border",
                        "group"
                      )}
                    >
                      <span className={cn(
                        "flex-grow text-sm transition-colors",
                        isSelected ? "text-foreground font-medium" : "text-muted-foreground group-hover:text-foreground"
                      )}>
                        {opt.label}
                      </span>
                      {isSelected && (
                        <div className="w-2 h-2 rounded-full bg-brand-500 shadow-sm ml-2" />
                      )}
                    </button>
                  )
                })}
                {q.allowCustom && (
                  <div className={cn(
                    "relative flex items-center w-full px-4 py-2 transition-all duration-200 rounded-xl border",
                    answers[q.id]?.startsWith('custom:')
                      ? "bg-background border-brand-500/30 ring-1 ring-brand-500/10"
                      : "bg-transparent border-transparent"
                  )}>
                    <Input
                      placeholder="Type something else..."
                      value={answers[q.id]?.startsWith('custom:') ? answers[q.id].slice(7) : ''}
                      onChange={e => setAnswers(a => ({ ...a, [q.id]: e.target.value ? `custom:${e.target.value}` : '' }))}
                      disabled={disabled || submitting}
                      className="text-sm border-0 bg-transparent px-0 focus-visible:ring-0 placeholder:text-muted-foreground/50 h-auto py-1 shadow-none"
                    />
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 pt-2">
          <Button variant="ghost" size="sm" onClick={onCancel} disabled={disabled || submitting} className="text-muted-foreground hover:text-foreground">
            Cancel
          </Button>
          <Button
            size="sm"
            onClick={handleSubmit}
            disabled={disabled || submitting || !allAnswered}
            className="bg-brand-500 hover:bg-brand-600 text-white shadow-lg shadow-brand-500/25 transition-all duration-300 px-6"
          >
            {submitting ? 'Starting...' : 'Start Research'}
          </Button>
        </div>
      </div>
    </div>
  )
}
