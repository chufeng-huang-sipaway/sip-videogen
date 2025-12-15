import { cn } from '@/lib/utils'

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
 * Transform technical skill names into user-friendly labels.
 */
const toFriendlySkillName = (skill: string): string => {
  const skillMappings: Record<string, string> = {
    'lifestyle-imagery': 'lifestyle imagery',
    'image-prompt-engineering': 'image prompts',
    'brand-identity': 'brand identity',
    'visual-design': 'visual design',
    'color-theory': 'color theory',
    'typography': 'typography',
  }
  return skillMappings[skill] || skill.replace(/-/g, ' ')
}

/**
 * Format skills list into a natural language string.
 */
const formatSkillsSubtitle = (skills: string[]): string => {
  if (!skills || skills.length === 0) return ''

  const friendlySkills = skills.map(toFriendlySkillName)

  if (friendlySkills.length === 1) {
    return `with ${friendlySkills[0]} expertise`
  }

  if (friendlySkills.length === 2) {
    return `with ${friendlySkills[0]} & ${friendlySkills[1]} expertise`
  }

  // 3+ skills: "with X, Y & Z expertise"
  const lastSkill = friendlySkills.pop()
  return `with ${friendlySkills.join(', ')} & ${lastSkill} expertise`
}

/**
 * Get the indicator color class based on activity type.
 */
const getIndicatorColorClass = (type: ActivityType): string => {
  switch (type) {
    case 'thinking':
      return 'bg-sky-500'
    case 'tool_start':
      return 'bg-emerald-500'
    case 'skill_loaded':
      return 'bg-amber-500'
    default:
      return 'bg-gray-400'
  }
}

/**
 * Get the ping animation color class based on activity type.
 */
const getPingColorClass = (type: ActivityType): string => {
  switch (type) {
    case 'thinking':
      return 'bg-sky-400'
    case 'tool_start':
      return 'bg-emerald-400'
    case 'skill_loaded':
      return 'bg-amber-400'
    default:
      return 'bg-gray-300'
  }
}

/**
 * Pulsing indicator dot with breathing animation.
 */
function PulsingIndicator({ type }: { type: ActivityType }) {
  return (
    <span className="relative flex h-2.5 w-2.5">
      {/* Ping animation layer */}
      <span
        className={cn(
          'absolute inline-flex h-full w-full animate-ping rounded-full opacity-75',
          getPingColorClass(type)
        )}
      />
      {/* Solid dot layer */}
      <span
        className={cn(
          'relative inline-flex h-2.5 w-2.5 rounded-full',
          getIndicatorColorClass(type)
        )}
      />
    </span>
  )
}

/**
 * Activity indicator component - Option C: Action-Focused with Subtle Context
 *
 * Shows the main action as primary text with a pulsing dot,
 * and skills as a subtle subtitle below for context.
 */
export function ActivityIndicator({ type, message, skills, className }: ActivityIndicatorProps) {
  const friendlyMessage = toFriendlyMessage(message)
  const skillsSubtitle = formatSkillsSubtitle(skills || [])
  const hasSkills = skillsSubtitle.length > 0

  return (
    <div
      className={cn(
        'inline-flex flex-col rounded-2xl',
        'bg-gray-100/80 dark:bg-gray-800/80',
        'px-4 py-2.5',
        'transition-all duration-200',
        className
      )}
    >
      {/* Main action line */}
      <div className="flex items-center gap-2.5">
        <PulsingIndicator type={type} />
        <span className="text-sm font-medium text-gray-700 dark:text-gray-200">
          {friendlyMessage}
        </span>
      </div>

      {/* Skills subtitle - subtle context */}
      {hasSkills && (
        <span className="text-xs text-gray-500 dark:text-gray-400 mt-1 ml-5">
          {skillsSubtitle}
        </span>
      )}
    </div>
  )
}
