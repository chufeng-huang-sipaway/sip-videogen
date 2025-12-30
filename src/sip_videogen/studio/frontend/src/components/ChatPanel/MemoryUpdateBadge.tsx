import { Brain } from 'lucide-react'

interface Props {
  message: string
}

export function MemoryUpdateBadge({ message }: Props) {
  return (
    <div className="flex items-center gap-2 mt-2 p-2 bg-brand-a10 rounded-lg text-sm">
      <Brain className="h-4 w-4 text-brand-500 flex-shrink-0" />
      <span className="text-brand-600 dark:text-brand-500">{message}</span>
    </div>
  )
}
