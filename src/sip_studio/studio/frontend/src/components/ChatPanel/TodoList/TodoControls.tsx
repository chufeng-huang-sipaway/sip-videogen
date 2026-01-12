//TodoControls component - stop button only
import { Button } from '@/components/ui/button'
import { Square } from 'lucide-react'

interface TodoControlsProps {
  onStop: () => void
}

export function TodoControls({ onStop }: TodoControlsProps) {
  return (
    <div className="flex border-t border-border/30 pt-3">
      <Button variant="ghost" size="sm" onClick={onStop} className="ml-auto flex items-center gap-2 text-xs text-muted-foreground hover:bg-destructive/10 hover:text-destructive">
        <Square className="h-3 w-3 fill-current" />
        Stop Generation
      </Button>
    </div>
  )
}
