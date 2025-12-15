import { useCallback, useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { bridge } from '@/lib/bridge'
import type { Interaction } from '@/lib/bridge'

interface Props {
  interaction: Interaction
  onSelect: (selection: string) => void
  disabled?: boolean
}

export function InteractionRenderer({ interaction, onSelect, disabled }: Props) {
  const [customValue, setCustomValue] = useState('')
  const [imagePreviews, setImagePreviews] = useState<Record<string, string>>({})

  const loadImagePreview = useCallback(
    async (path: string) => {
      if (imagePreviews[path]) return
      try {
        const dataUrl = await bridge.getAssetThumbnail(path)
        setImagePreviews(prev => ({ ...prev, [path]: dataUrl }))
      } catch (err) {
        console.error('Failed to load preview:', err)
      }
    },
    [imagePreviews]
  )

  useEffect(() => {
    if (interaction.type !== 'image_select') return
    for (const path of interaction.image_paths) {
      if (!imagePreviews[path]) void loadImagePreview(path)
    }
  }, [interaction, imagePreviews, loadImagePreview])

  if (interaction.type === 'choices') {
    return (
      <div className="mt-3 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg space-y-2">
        <p className="text-sm font-medium">{interaction.question}</p>
        <div className="flex flex-wrap gap-2">
          {interaction.choices.map((choice) => (
            <Button
              key={choice}
              variant="outline"
              size="sm"
              onClick={() => onSelect(choice)}
              disabled={disabled}
            >
              {choice}
            </Button>
          ))}
        </div>
        {interaction.allow_custom && (
          <div className="flex gap-2 mt-2">
            <Input
              placeholder="Or type something else..."
              value={customValue}
              onChange={(e) => setCustomValue(e.target.value)}
              disabled={disabled}
              className="text-sm"
              onKeyDown={(e) => {
                if (e.key === 'Enter' && customValue.trim()) {
                  onSelect(customValue)
                }
              }}
            />
            <Button
              size="sm"
              onClick={() => onSelect(customValue)}
              disabled={disabled || !customValue.trim()}
            >
              Send
            </Button>
          </div>
        )}
      </div>
    )
  }

  if (interaction.type === 'image_select') {
    return (
      <div className="mt-3 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg space-y-2">
        <p className="text-sm font-medium">{interaction.question}</p>
        <div className="grid grid-cols-2 gap-2">
          {interaction.image_paths.map((path, i) => (
            <button
              key={path}
              onClick={() => onSelect(`Option ${i + 1}: ${interaction.labels[i]}`)}
              disabled={disabled}
              className="relative group border rounded-lg overflow-hidden hover:ring-2 hover:ring-blue-500 disabled:opacity-50 text-left"
            >
              {imagePreviews[path] ? (
                <img
                  src={imagePreviews[path]}
                  alt={interaction.labels[i]}
                  className="w-full h-32 object-cover"
                />
              ) : (
                <div className="w-full h-32 bg-gray-100 dark:bg-gray-800 flex items-center justify-center">
                  <span className="text-gray-400 text-xs">Loading...</span>
                </div>
              )}
              <div className="absolute bottom-0 left-0 right-0 bg-black/60 text-white text-xs p-1">
                {interaction.labels[i]}
              </div>
            </button>
          ))}
        </div>
      </div>
    )
  }

  return null
}
