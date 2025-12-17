import { useState, useCallback } from 'react'
import { Save, AlertCircle, CheckCircle2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Spinner } from '@/components/ui/spinner'
import { MemorySection } from '../MemorySection'
import { bridge } from '@/lib/bridge'
import type { BrandCoreIdentity, BrandIdentityFull } from '@/types/brand-identity'

interface CoreSectionProps {
  /** Current core identity data */
  data: BrandCoreIdentity
  /** Called when identity is updated (to refresh parent state) */
  onIdentityUpdate: (identity: BrandIdentityFull) => void
}

/**
 * CoreSection - Displays and edits core brand identity.
 *
 * Fields:
 * - name: Brand name
 * - tagline: Short brand tagline
 * - mission: Brand mission statement
 * - brand_story: Full brand story/narrative
 * - values: List of brand values
 *
 * Uses MemorySection wrapper for collapse/expand and edit mode toggle.
 */
export function CoreSection({ data, onIdentityUpdate }: CoreSectionProps) {
  // Edit state - local copy of data being edited
  const [editData, setEditData] = useState<BrandCoreIdentity | null>(null)
  const [isSaving, setIsSaving] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)
  const [saveSuccess, setSaveSuccess] = useState(false)

  // Handle entering edit mode
  const handleEditModeChange = useCallback(
    (isEditing: boolean) => {
      if (isEditing) {
        // Deep copy current data for editing
        setEditData({ ...data, values: [...data.values] })
        setSaveError(null)
        setSaveSuccess(false)
      } else {
        // Discard changes
        setEditData(null)
        setSaveError(null)
        setSaveSuccess(false)
      }
    },
    [data]
  )

  // Handle save
  const handleSave = useCallback(async () => {
    if (!editData) return

    setIsSaving(true)
    setSaveError(null)
    setSaveSuccess(false)

    try {
      const updatedIdentity = await bridge.updateBrandIdentitySection('core', editData)
      onIdentityUpdate(updatedIdentity)
      setSaveSuccess(true)
      // Clear edit mode after successful save
      setEditData(null)
    } catch (err) {
      console.error('[CoreSection] Save failed:', err)
      setSaveError(err instanceof Error ? err.message : 'Failed to save changes')
    } finally {
      setIsSaving(false)
    }
  }, [editData, onIdentityUpdate])

  // Handle field changes
  const updateField = <K extends keyof BrandCoreIdentity>(
    field: K,
    value: BrandCoreIdentity[K]
  ) => {
    if (!editData) return
    setEditData({ ...editData, [field]: value })
  }

  // Handle values list changes
  const updateValue = (index: number, newValue: string) => {
    if (!editData) return
    const newValues = [...editData.values]
    newValues[index] = newValue
    setEditData({ ...editData, values: newValues })
  }

  const addValue = () => {
    if (!editData) return
    setEditData({ ...editData, values: [...editData.values, ''] })
  }

  const removeValue = (index: number) => {
    if (!editData) return
    const newValues = editData.values.filter((_, i) => i !== index)
    setEditData({ ...editData, values: newValues })
  }

  // View mode content
  const viewContent = (
    <div className="space-y-4">
      {/* Success message */}
      {saveSuccess && (
        <Alert className="bg-green-500/10 border-green-500/20">
          <CheckCircle2 className="h-4 w-4 text-green-500" />
          <AlertDescription className="text-green-700 dark:text-green-400">
            Changes saved. AI context refreshed automatically.
          </AlertDescription>
        </Alert>
      )}

      <div className="grid gap-4">
        <div>
          <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
            Brand Name
          </label>
          <p className="mt-1 text-sm">{data.name}</p>
        </div>

        <div>
          <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
            Tagline
          </label>
          <p className="mt-1 text-sm">{data.tagline}</p>
        </div>

        <div>
          <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
            Mission
          </label>
          <p className="mt-1 text-sm whitespace-pre-wrap">{data.mission}</p>
        </div>

        <div>
          <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
            Brand Story
          </label>
          <p className="mt-1 text-sm whitespace-pre-wrap">{data.brand_story}</p>
        </div>

        <div>
          <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
            Values
          </label>
          <div className="mt-1 flex flex-wrap gap-2">
            {data.values.map((value, index) => (
              <span
                key={index}
                className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-300"
              >
                {value}
              </span>
            ))}
          </div>
        </div>
      </div>
    </div>
  )

  // Edit mode content
  const editContent = editData && (
    <div className="space-y-4">
      {/* Error message */}
      {saveError && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{saveError}</AlertDescription>
        </Alert>
      )}

      <div className="grid gap-4">
        <div>
          <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
            Brand Name
          </label>
          <Input
            value={editData.name}
            onChange={(e) => updateField('name', e.target.value)}
            className="mt-1"
            disabled={isSaving}
          />
        </div>

        <div>
          <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
            Tagline
          </label>
          <Input
            value={editData.tagline}
            onChange={(e) => updateField('tagline', e.target.value)}
            className="mt-1"
            disabled={isSaving}
          />
        </div>

        <div>
          <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
            Mission
          </label>
          <textarea
            value={editData.mission}
            onChange={(e) => updateField('mission', e.target.value)}
            className="mt-1 w-full min-h-[80px] rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
            disabled={isSaving}
          />
        </div>

        <div>
          <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
            Brand Story
          </label>
          <textarea
            value={editData.brand_story}
            onChange={(e) => updateField('brand_story', e.target.value)}
            className="mt-1 w-full min-h-[120px] rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
            disabled={isSaving}
          />
        </div>

        <div>
          <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
            Values
          </label>
          <div className="mt-1 space-y-2">
            {editData.values.map((value, index) => (
              <div key={index} className="flex gap-2">
                <Input
                  value={value}
                  onChange={(e) => updateValue(index, e.target.value)}
                  placeholder={`Value ${index + 1}`}
                  disabled={isSaving}
                  className="flex-1"
                />
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => removeValue(index)}
                  disabled={isSaving || editData.values.length <= 1}
                  className="px-2 text-muted-foreground hover:text-destructive"
                >
                  &times;
                </Button>
              </div>
            ))}
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={addValue}
              disabled={isSaving}
              className="w-full"
            >
              + Add Value
            </Button>
          </div>
        </div>
      </div>

      {/* Save button */}
      <div className="flex justify-end pt-2 border-t border-border">
        <Button onClick={handleSave} disabled={isSaving} className="gap-1.5">
          {isSaving ? (
            <>
              <Spinner className="h-4 w-4" />
              Saving...
            </>
          ) : (
            <>
              <Save className="h-4 w-4" />
              Save Changes
            </>
          )}
        </Button>
      </div>
    </div>
  )

  return (
    <MemorySection
      id="core"
      title="Core Identity"
      subtitle={`${data.name} - ${data.tagline}`}
      editable
      isSaving={isSaving}
      onEditModeChange={handleEditModeChange}
      editContent={editContent}
    >
      {viewContent}
    </MemorySection>
  )
}
