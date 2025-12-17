import { useState, useCallback } from 'react'
import { Save, AlertCircle, CheckCircle2, Plus, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Spinner } from '@/components/ui/spinner'
import { MemorySection } from '../MemorySection'
import { bridge } from '@/lib/bridge'
import type {
  VisualIdentity,
  BrandIdentityFull,
  ColorDefinition,
  TypographyRule,
} from '@/types/brand-identity'

interface VisualSectionProps {
  /** Current visual identity data */
  data: VisualIdentity
  /** Called when identity is updated (to refresh parent state) */
  onIdentityUpdate: (identity: BrandIdentityFull) => void
}

/**
 * VisualSection - Displays and edits visual identity.
 *
 * Fields:
 * - Colors: primary_colors, secondary_colors, accent_colors
 * - Typography: typography rules
 * - Imagery: imagery_style, imagery_keywords, imagery_avoid
 * - Materials: materials list
 * - Logo: logo_description, logo_usage_rules
 * - Overall: overall_aesthetic, style_keywords
 *
 * Uses MemorySection wrapper for collapse/expand and edit mode toggle.
 */
export function VisualSection({ data, onIdentityUpdate }: VisualSectionProps) {
  // Edit state - local copy of data being edited
  const [editData, setEditData] = useState<VisualIdentity | null>(null)
  const [isSaving, setIsSaving] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)
  const [saveSuccess, setSaveSuccess] = useState(false)

  // Deep copy helper for colors and typography
  const deepCopyData = (d: VisualIdentity): VisualIdentity => ({
    ...d,
    primary_colors: d.primary_colors.map((c) => ({ ...c })),
    secondary_colors: d.secondary_colors.map((c) => ({ ...c })),
    accent_colors: d.accent_colors.map((c) => ({ ...c })),
    typography: d.typography.map((t) => ({ ...t })),
    imagery_keywords: [...d.imagery_keywords],
    imagery_avoid: [...d.imagery_avoid],
    materials: [...d.materials],
    style_keywords: [...d.style_keywords],
  })

  // Handle entering edit mode
  const handleEditModeChange = useCallback(
    (isEditing: boolean) => {
      if (isEditing) {
        setEditData(deepCopyData(data))
        setSaveError(null)
        setSaveSuccess(false)
      } else {
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
      const updatedIdentity = await bridge.updateBrandIdentitySection('visual', editData)
      onIdentityUpdate(updatedIdentity)
      setSaveSuccess(true)
      setEditData(null)
    } catch (err) {
      console.error('[VisualSection] Save failed:', err)
      setSaveError(err instanceof Error ? err.message : 'Failed to save changes')
    } finally {
      setIsSaving(false)
    }
  }, [editData, onIdentityUpdate])

  // Color array helpers
  const updateColor = (
    colorType: 'primary_colors' | 'secondary_colors' | 'accent_colors',
    index: number,
    field: keyof ColorDefinition,
    value: string
  ) => {
    if (!editData) return
    const newColors = [...editData[colorType]]
    newColors[index] = { ...newColors[index], [field]: value }
    setEditData({ ...editData, [colorType]: newColors })
  }

  const addColor = (colorType: 'primary_colors' | 'secondary_colors' | 'accent_colors') => {
    if (!editData) return
    const newColor: ColorDefinition = { hex: '#000000', name: '', usage: '' }
    setEditData({ ...editData, [colorType]: [...editData[colorType], newColor] })
  }

  const removeColor = (
    colorType: 'primary_colors' | 'secondary_colors' | 'accent_colors',
    index: number
  ) => {
    if (!editData) return
    const newColors = editData[colorType].filter((_, i) => i !== index)
    setEditData({ ...editData, [colorType]: newColors })
  }

  // Typography helpers
  const updateTypography = (index: number, field: keyof TypographyRule, value: string) => {
    if (!editData) return
    const newTypo = [...editData.typography]
    newTypo[index] = { ...newTypo[index], [field]: value }
    setEditData({ ...editData, typography: newTypo })
  }

  const addTypography = () => {
    if (!editData) return
    const newRule: TypographyRule = { role: '', family: '', weight: '', style_notes: '' }
    setEditData({ ...editData, typography: [...editData.typography, newRule] })
  }

  const removeTypography = (index: number) => {
    if (!editData) return
    const newTypo = editData.typography.filter((_, i) => i !== index)
    setEditData({ ...editData, typography: newTypo })
  }

  // String array helpers
  const updateStringArray = (
    field: 'imagery_keywords' | 'imagery_avoid' | 'materials' | 'style_keywords',
    index: number,
    value: string
  ) => {
    if (!editData) return
    const newArr = [...editData[field]]
    newArr[index] = value
    setEditData({ ...editData, [field]: newArr })
  }

  const addToStringArray = (
    field: 'imagery_keywords' | 'imagery_avoid' | 'materials' | 'style_keywords'
  ) => {
    if (!editData) return
    setEditData({ ...editData, [field]: [...editData[field], ''] })
  }

  const removeFromStringArray = (
    field: 'imagery_keywords' | 'imagery_avoid' | 'materials' | 'style_keywords',
    index: number
  ) => {
    if (!editData) return
    const newArr = editData[field].filter((_, i) => i !== index)
    setEditData({ ...editData, [field]: newArr })
  }

  // Simple field update
  const updateField = <K extends keyof VisualIdentity>(field: K, value: VisualIdentity[K]) => {
    if (!editData) return
    setEditData({ ...editData, [field]: value })
  }

  // Color swatch component for view mode
  const ColorSwatch = ({ color }: { color: ColorDefinition }) => (
    <div className="flex items-center gap-2 p-2 rounded-md bg-muted/50">
      <div
        className="w-6 h-6 rounded border border-border shadow-sm"
        style={{ backgroundColor: color.hex }}
      />
      <div className="flex-1 min-w-0">
        <div className="text-sm font-medium truncate">{color.name || color.hex}</div>
        <div className="text-xs text-muted-foreground truncate">{color.usage}</div>
      </div>
    </div>
  )

  // View mode content
  const viewContent = (
    <div className="space-y-6">
      {saveSuccess && (
        <Alert className="bg-green-500/10 border-green-500/20">
          <CheckCircle2 className="h-4 w-4 text-green-500" />
          <AlertDescription className="text-green-700 dark:text-green-400">
            Changes saved. AI context refreshed automatically.
          </AlertDescription>
        </Alert>
      )}

      {/* Colors */}
      <div className="space-y-4">
        <h4 className="text-sm font-medium">Color Palette</h4>

        {data.primary_colors.length > 0 && (
          <div>
            <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
              Primary Colors
            </label>
            <div className="mt-1 grid gap-2 sm:grid-cols-2">
              {data.primary_colors.map((color, i) => (
                <ColorSwatch key={i} color={color} />
              ))}
            </div>
          </div>
        )}

        {data.secondary_colors.length > 0 && (
          <div>
            <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
              Secondary Colors
            </label>
            <div className="mt-1 grid gap-2 sm:grid-cols-2">
              {data.secondary_colors.map((color, i) => (
                <ColorSwatch key={i} color={color} />
              ))}
            </div>
          </div>
        )}

        {data.accent_colors.length > 0 && (
          <div>
            <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
              Accent Colors
            </label>
            <div className="mt-1 grid gap-2 sm:grid-cols-2">
              {data.accent_colors.map((color, i) => (
                <ColorSwatch key={i} color={color} />
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Typography */}
      {data.typography.length > 0 && (
        <div>
          <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
            Typography
          </label>
          <div className="mt-1 space-y-2">
            {data.typography.map((rule, i) => (
              <div key={i} className="p-2 rounded-md bg-muted/50">
                <div className="text-sm font-medium">{rule.role}</div>
                <div className="text-xs text-muted-foreground">
                  {rule.family} - {rule.weight}
                </div>
                {rule.style_notes && (
                  <div className="text-xs text-muted-foreground mt-1">{rule.style_notes}</div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Imagery */}
      <div className="space-y-4">
        <h4 className="text-sm font-medium">Imagery</h4>

        <div>
          <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
            Style
          </label>
          <p className="mt-1 text-sm whitespace-pre-wrap">{data.imagery_style}</p>
        </div>

        {data.imagery_keywords.length > 0 && (
          <div>
            <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
              Keywords
            </label>
            <div className="mt-1 flex flex-wrap gap-2">
              {data.imagery_keywords.map((kw, i) => (
                <span
                  key={i}
                  className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300"
                >
                  {kw}
                </span>
              ))}
            </div>
          </div>
        )}

        {data.imagery_avoid.length > 0 && (
          <div>
            <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
              Avoid
            </label>
            <div className="mt-1 flex flex-wrap gap-2">
              {data.imagery_avoid.map((item, i) => (
                <span
                  key={i}
                  className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300"
                >
                  {item}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Materials */}
      {data.materials.length > 0 && (
        <div>
          <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
            Materials & Textures
          </label>
          <div className="mt-1 flex flex-wrap gap-2">
            {data.materials.map((mat, i) => (
              <span
                key={i}
                className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300"
              >
                {mat}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Logo */}
      <div className="space-y-4">
        <h4 className="text-sm font-medium">Logo</h4>

        <div>
          <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
            Description
          </label>
          <p className="mt-1 text-sm whitespace-pre-wrap">{data.logo_description}</p>
        </div>

        <div>
          <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
            Usage Rules
          </label>
          <p className="mt-1 text-sm whitespace-pre-wrap">{data.logo_usage_rules}</p>
        </div>
      </div>

      {/* Overall Aesthetic */}
      <div className="space-y-4">
        <h4 className="text-sm font-medium">Overall Aesthetic</h4>

        <div>
          <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
            Description
          </label>
          <p className="mt-1 text-sm whitespace-pre-wrap">{data.overall_aesthetic}</p>
        </div>

        {data.style_keywords.length > 0 && (
          <div>
            <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
              Style Keywords
            </label>
            <div className="mt-1 flex flex-wrap gap-2">
              {data.style_keywords.map((kw, i) => (
                <span
                  key={i}
                  className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-300"
                >
                  {kw}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )

  // Edit mode content
  const editContent = editData && (
    <div className="space-y-6">
      {saveError && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{saveError}</AlertDescription>
        </Alert>
      )}

      {/* Colors */}
      <div className="space-y-4">
        <h4 className="text-sm font-medium">Color Palette</h4>

        {/* Primary Colors */}
        <div>
          <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
            Primary Colors
          </label>
          <div className="mt-1 space-y-2">
            {editData.primary_colors.map((color, i) => (
              <div key={i} className="flex gap-2 items-start">
                <input
                  type="color"
                  value={color.hex}
                  onChange={(e) => updateColor('primary_colors', i, 'hex', e.target.value)}
                  disabled={isSaving}
                  className="w-10 h-9 rounded border border-input cursor-pointer"
                />
                <Input
                  value={color.hex}
                  onChange={(e) => updateColor('primary_colors', i, 'hex', e.target.value)}
                  disabled={isSaving}
                  placeholder="#000000"
                  className="w-24"
                />
                <Input
                  value={color.name}
                  onChange={(e) => updateColor('primary_colors', i, 'name', e.target.value)}
                  disabled={isSaving}
                  placeholder="Name"
                  className="flex-1"
                />
                <Input
                  value={color.usage}
                  onChange={(e) => updateColor('primary_colors', i, 'usage', e.target.value)}
                  disabled={isSaving}
                  placeholder="Usage"
                  className="flex-1"
                />
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  onClick={() => removeColor('primary_colors', i)}
                  disabled={isSaving}
                  className="text-muted-foreground hover:text-destructive shrink-0"
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>
            ))}
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => addColor('primary_colors')}
              disabled={isSaving}
              className="gap-1"
            >
              <Plus className="h-3 w-3" /> Add Primary
            </Button>
          </div>
        </div>

        {/* Secondary Colors */}
        <div>
          <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
            Secondary Colors
          </label>
          <div className="mt-1 space-y-2">
            {editData.secondary_colors.map((color, i) => (
              <div key={i} className="flex gap-2 items-start">
                <input
                  type="color"
                  value={color.hex}
                  onChange={(e) => updateColor('secondary_colors', i, 'hex', e.target.value)}
                  disabled={isSaving}
                  className="w-10 h-9 rounded border border-input cursor-pointer"
                />
                <Input
                  value={color.hex}
                  onChange={(e) => updateColor('secondary_colors', i, 'hex', e.target.value)}
                  disabled={isSaving}
                  placeholder="#000000"
                  className="w-24"
                />
                <Input
                  value={color.name}
                  onChange={(e) => updateColor('secondary_colors', i, 'name', e.target.value)}
                  disabled={isSaving}
                  placeholder="Name"
                  className="flex-1"
                />
                <Input
                  value={color.usage}
                  onChange={(e) => updateColor('secondary_colors', i, 'usage', e.target.value)}
                  disabled={isSaving}
                  placeholder="Usage"
                  className="flex-1"
                />
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  onClick={() => removeColor('secondary_colors', i)}
                  disabled={isSaving}
                  className="text-muted-foreground hover:text-destructive shrink-0"
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>
            ))}
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => addColor('secondary_colors')}
              disabled={isSaving}
              className="gap-1"
            >
              <Plus className="h-3 w-3" /> Add Secondary
            </Button>
          </div>
        </div>

        {/* Accent Colors */}
        <div>
          <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
            Accent Colors
          </label>
          <div className="mt-1 space-y-2">
            {editData.accent_colors.map((color, i) => (
              <div key={i} className="flex gap-2 items-start">
                <input
                  type="color"
                  value={color.hex}
                  onChange={(e) => updateColor('accent_colors', i, 'hex', e.target.value)}
                  disabled={isSaving}
                  className="w-10 h-9 rounded border border-input cursor-pointer"
                />
                <Input
                  value={color.hex}
                  onChange={(e) => updateColor('accent_colors', i, 'hex', e.target.value)}
                  disabled={isSaving}
                  placeholder="#000000"
                  className="w-24"
                />
                <Input
                  value={color.name}
                  onChange={(e) => updateColor('accent_colors', i, 'name', e.target.value)}
                  disabled={isSaving}
                  placeholder="Name"
                  className="flex-1"
                />
                <Input
                  value={color.usage}
                  onChange={(e) => updateColor('accent_colors', i, 'usage', e.target.value)}
                  disabled={isSaving}
                  placeholder="Usage"
                  className="flex-1"
                />
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  onClick={() => removeColor('accent_colors', i)}
                  disabled={isSaving}
                  className="text-muted-foreground hover:text-destructive shrink-0"
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>
            ))}
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => addColor('accent_colors')}
              disabled={isSaving}
              className="gap-1"
            >
              <Plus className="h-3 w-3" /> Add Accent
            </Button>
          </div>
        </div>
      </div>

      {/* Typography */}
      <div>
        <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
          Typography
        </label>
        <div className="mt-1 space-y-3">
          {editData.typography.map((rule, i) => (
            <div key={i} className="p-3 rounded-md border border-border space-y-2">
              <div className="flex gap-2">
                <Input
                  value={rule.role}
                  onChange={(e) => updateTypography(i, 'role', e.target.value)}
                  disabled={isSaving}
                  placeholder="Role (e.g., Headline)"
                  className="flex-1"
                />
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  onClick={() => removeTypography(i)}
                  disabled={isSaving}
                  className="text-muted-foreground hover:text-destructive shrink-0"
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>
              <div className="flex gap-2">
                <Input
                  value={rule.family}
                  onChange={(e) => updateTypography(i, 'family', e.target.value)}
                  disabled={isSaving}
                  placeholder="Font Family"
                  className="flex-1"
                />
                <Input
                  value={rule.weight}
                  onChange={(e) => updateTypography(i, 'weight', e.target.value)}
                  disabled={isSaving}
                  placeholder="Weight"
                  className="w-28"
                />
              </div>
              <Input
                value={rule.style_notes}
                onChange={(e) => updateTypography(i, 'style_notes', e.target.value)}
                disabled={isSaving}
                placeholder="Style notes"
              />
            </div>
          ))}
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={addTypography}
            disabled={isSaving}
            className="w-full gap-1"
          >
            <Plus className="h-3 w-3" /> Add Typography Rule
          </Button>
        </div>
      </div>

      {/* Imagery */}
      <div className="space-y-4">
        <h4 className="text-sm font-medium">Imagery</h4>

        <div>
          <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
            Style
          </label>
          <textarea
            value={editData.imagery_style}
            onChange={(e) => updateField('imagery_style', e.target.value)}
            disabled={isSaving}
            className="mt-1 w-full min-h-[80px] rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
          />
        </div>

        {/* Imagery Keywords */}
        <div>
          <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
            Keywords
          </label>
          <div className="mt-1 space-y-2">
            {editData.imagery_keywords.map((kw, i) => (
              <div key={i} className="flex gap-2">
                <Input
                  value={kw}
                  onChange={(e) => updateStringArray('imagery_keywords', i, e.target.value)}
                  disabled={isSaving}
                  placeholder="Keyword"
                  className="flex-1"
                />
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  onClick={() => removeFromStringArray('imagery_keywords', i)}
                  disabled={isSaving}
                  className="text-muted-foreground hover:text-destructive shrink-0"
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>
            ))}
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => addToStringArray('imagery_keywords')}
              disabled={isSaving}
              className="gap-1"
            >
              <Plus className="h-3 w-3" /> Add Keyword
            </Button>
          </div>
        </div>

        {/* Imagery Avoid */}
        <div>
          <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
            Avoid
          </label>
          <div className="mt-1 space-y-2">
            {editData.imagery_avoid.map((item, i) => (
              <div key={i} className="flex gap-2">
                <Input
                  value={item}
                  onChange={(e) => updateStringArray('imagery_avoid', i, e.target.value)}
                  disabled={isSaving}
                  placeholder="Item to avoid"
                  className="flex-1"
                />
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  onClick={() => removeFromStringArray('imagery_avoid', i)}
                  disabled={isSaving}
                  className="text-muted-foreground hover:text-destructive shrink-0"
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>
            ))}
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => addToStringArray('imagery_avoid')}
              disabled={isSaving}
              className="gap-1"
            >
              <Plus className="h-3 w-3" /> Add Item
            </Button>
          </div>
        </div>
      </div>

      {/* Materials */}
      <div>
        <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
          Materials & Textures
        </label>
        <div className="mt-1 space-y-2">
          {editData.materials.map((mat, i) => (
            <div key={i} className="flex gap-2">
              <Input
                value={mat}
                onChange={(e) => updateStringArray('materials', i, e.target.value)}
                disabled={isSaving}
                placeholder="Material"
                className="flex-1"
              />
              <Button
                type="button"
                variant="ghost"
                size="icon"
                onClick={() => removeFromStringArray('materials', i)}
                disabled={isSaving}
                className="text-muted-foreground hover:text-destructive shrink-0"
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
          ))}
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => addToStringArray('materials')}
            disabled={isSaving}
            className="gap-1"
          >
            <Plus className="h-3 w-3" /> Add Material
          </Button>
        </div>
      </div>

      {/* Logo */}
      <div className="space-y-4">
        <h4 className="text-sm font-medium">Logo</h4>

        <div>
          <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
            Description
          </label>
          <textarea
            value={editData.logo_description}
            onChange={(e) => updateField('logo_description', e.target.value)}
            disabled={isSaving}
            className="mt-1 w-full min-h-[80px] rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
          />
        </div>

        <div>
          <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
            Usage Rules
          </label>
          <textarea
            value={editData.logo_usage_rules}
            onChange={(e) => updateField('logo_usage_rules', e.target.value)}
            disabled={isSaving}
            className="mt-1 w-full min-h-[80px] rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
          />
        </div>
      </div>

      {/* Overall Aesthetic */}
      <div className="space-y-4">
        <h4 className="text-sm font-medium">Overall Aesthetic</h4>

        <div>
          <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
            Description
          </label>
          <textarea
            value={editData.overall_aesthetic}
            onChange={(e) => updateField('overall_aesthetic', e.target.value)}
            disabled={isSaving}
            className="mt-1 w-full min-h-[80px] rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
          />
        </div>

        {/* Style Keywords */}
        <div>
          <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
            Style Keywords
          </label>
          <div className="mt-1 space-y-2">
            {editData.style_keywords.map((kw, i) => (
              <div key={i} className="flex gap-2">
                <Input
                  value={kw}
                  onChange={(e) => updateStringArray('style_keywords', i, e.target.value)}
                  disabled={isSaving}
                  placeholder="Keyword"
                  className="flex-1"
                />
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  onClick={() => removeFromStringArray('style_keywords', i)}
                  disabled={isSaving}
                  className="text-muted-foreground hover:text-destructive shrink-0"
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>
            ))}
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => addToStringArray('style_keywords')}
              disabled={isSaving}
              className="gap-1"
            >
              <Plus className="h-3 w-3" /> Add Keyword
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

  // Generate subtitle from data
  const colorCount =
    data.primary_colors.length + data.secondary_colors.length + data.accent_colors.length
  const subtitle = `${colorCount} colors, ${data.typography.length} typography rules`

  return (
    <MemorySection
      id="visual"
      title="Visual Identity"
      subtitle={subtitle}
      editable
      isSaving={isSaving}
      onEditModeChange={handleEditModeChange}
      editContent={editContent}
    >
      {viewContent}
    </MemorySection>
  )
}
