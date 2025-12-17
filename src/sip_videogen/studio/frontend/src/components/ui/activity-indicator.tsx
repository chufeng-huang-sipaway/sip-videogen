import { cn } from '@/lib/utils'
import { Sparkles, Loader2 } from 'lucide-react'

export type ActivityType = 'thinking' | 'tool_start' | 'tool_end' | 'skill_loaded' | ''

interface ActivityIndicatorProps {
  type: ActivityType
  message: string
  skills?: string[]
  className?: string
}

/**
 * Transform technical tool/action names into user-friendly messages.
 */
const toFriendlyMessage = (message: string): string => {
  // Handle "Using X" tool messages
  const usingMatch = message.match(/^Using\s+(.+)$/i)
  if (usingMatch) {
    const toolName = usingMatch[1]
    // Map known tool names to friendly descriptions
    const toolMappings: Record<string, string> = {
      'generate_image': 'Creating your image...',
      'search_web': 'Searching the web...',
      'read_file': 'Reading file...',
      'write_file': 'Writing file...',
      'analyze_image': 'Analyzing image...',
      'get_brand_identity': 'Loading brand details...',
      'update_brand': 'Updating brand...',
    }
    return toolMappings[toolName] || `Working on ${toolName.replace(/_/g, ' ')}...`
  }

  // Handle "Thinking" messages
  if (message.toLowerCase().includes('thinking')) {
    return 'Thinking...'
  }

  // Return as-is if already friendly
  return message
}

/**
 * Activity indicator component - Minimalist & Elegant
 * 
 * Replaces the heavy bubble with a subtle text line + icon.
 */
export function ActivityIndicator({ message, skills, className }: ActivityIndicatorProps) {
  const friendlyMessage = toFriendlyMessage(message)

  // Decide which icon to show interactions
  const isImageGen = friendlyMessage.toLowerCase().includes('image')

  return (
    <div
      className={cn(
        'flex items-center gap-3 py-2 px-1 animate-in fade-in duration-300 slide-in-from-bottom-2',
        className
      )}
    >
      <div className="relative flex items-center justify-center h-6 w-6">
        {/* Animated background glow */}
        <div className="absolute inset-0 bg-primary/20 rounded-full blur-md animate-pulse" />

        {/* Icon based on activity */}
        {isImageGen ? (
          <Sparkles className="h-4 w-4 text-primary animate-pulse" />
        ) : (
          <Loader2 className="h-4 w-4 text-primary animate-spin" />
        )}
      </div>

      <div className="flex flex-col">
        <span className="text-sm font-medium text-foreground/80 tracking-tight">
          {friendlyMessage}
        </span>
        {skills && skills.length > 0 && (
          <span className="text-[10px] text-muted-foreground uppercase tracking-wider font-medium opacity-80">
            Using {skills.length} expert skill{skills.length !== 1 ? 's' : ''}
          </span>
        )}
      </div>
    </div>
  )
}
