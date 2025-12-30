import { useState } from 'react'
import { Brain, CheckCircle, ChevronDown, ChevronRight, Wrench } from 'lucide-react'
import type { ExecutionEvent } from '@/lib/bridge'

interface Props {
  events: ExecutionEvent[]
}

export function ExecutionTrace({ events }: Props) {
  const [isExpanded, setIsExpanded] = useState(false)

  if (!events || events.length === 0) return null

  const getIcon = (type: string) => {
    switch (type) {
      case 'thinking': return <Brain className="h-3 w-3 text-brand-500" />
      case 'thinking_step': return <CheckCircle className="h-3 w-3 text-success" />
      case 'tool_start': return <Wrench className="h-3 w-3 text-muted-foreground" />
      case 'tool_end': return <CheckCircle className="h-3 w-3 text-success" />
      default: return null
    }
  }

  return (
    <div className="mt-2 text-xs">
      <button
        type="button"
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex items-center gap-1 text-muted-foreground hover:text-foreground transition-colors"
      >
        {isExpanded ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
        View activity ({events.length} steps)
      </button>

      {isExpanded && (
        <div className="mt-2 pl-2 border-l-2 border-border space-y-1">
          {events.map((event, i) => (
            <div key={`${event.timestamp}-${i}`} className="flex items-start gap-2">
              {getIcon(event.type)}
              <span className="text-muted-foreground">{event.message}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
