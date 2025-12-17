import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import type { ColorDefinition } from '@/types/brand-identity';

interface ColorListEditorProps {
  /** Current list of color definitions */
  value: ColorDefinition[];
  /** Callback when list changes */
  onChange: (value: ColorDefinition[]) => void;
  /** Label text displayed above the list */
  label: string;
  /** Whether inputs are disabled */
  disabled?: boolean;
  /** Minimum number of items required (prevents removal below this count) */
  minItems?: number;
  /** Custom text for add button (defaults to "Add {label singular}") */
  addButtonText?: string;
  /** Additional class names for the container */
  className?: string;
}

/**
 * Reusable color list editor component.
 * Displays a list of color definitions with native color picker, hex input,
 * name, and usage fields. Supports add/remove functionality.
 *
 * Uses native `<input type="color">` to avoid additional dependencies.
 *
 * Used for editing arrays of ColorDefinition like primary_colors,
 * secondary_colors, and accent_colors in VisualIdentity.
 */
export function ColorListEditor({
  value,
  onChange,
  label,
  disabled = false,
  minItems = 0,
  addButtonText,
  className = '',
}: ColorListEditorProps) {
  const handleColorChange = (
    index: number,
    field: keyof ColorDefinition,
    newValue: string
  ) => {
    const newList = [...value];
    newList[index] = { ...newList[index], [field]: newValue };
    onChange(newList);
  };

  const handleAddColor = () => {
    const newColor: ColorDefinition = { hex: '#000000', name: '', usage: '' };
    onChange([...value, newColor]);
  };

  const handleRemoveColor = (index: number) => {
    const newList = value.filter((_, i) => i !== index);
    onChange(newList);
  };

  // Generate default add button text by removing trailing 's' from label
  const defaultAddText = `+ Add ${label.replace(/s$/, '')}`;
  const buttonText = addButtonText ?? defaultAddText;

  return (
    <div className={className}>
      <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
        {label}
      </label>
      <div className="mt-1 space-y-2">
        {value.map((color, index) => (
          <div key={index} className="flex gap-2 items-start">
            {/* Native color picker */}
            <input
              type="color"
              value={color.hex}
              onChange={(e) => handleColorChange(index, 'hex', e.target.value)}
              disabled={disabled}
              className="w-10 h-9 rounded border border-input cursor-pointer disabled:cursor-not-allowed disabled:opacity-50"
            />
            {/* Hex input */}
            <Input
              value={color.hex}
              onChange={(e) => handleColorChange(index, 'hex', e.target.value)}
              disabled={disabled}
              placeholder="#000000"
              className="w-24"
            />
            {/* Name input */}
            <Input
              value={color.name}
              onChange={(e) => handleColorChange(index, 'name', e.target.value)}
              disabled={disabled}
              placeholder="Name"
              className="flex-1"
            />
            {/* Usage input */}
            <Input
              value={color.usage}
              onChange={(e) => handleColorChange(index, 'usage', e.target.value)}
              disabled={disabled}
              placeholder="Usage"
              className="flex-1"
            />
            {/* Remove button */}
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => handleRemoveColor(index)}
              disabled={disabled || value.length <= minItems}
              className="px-2 text-muted-foreground hover:text-destructive shrink-0 h-9"
            >
              &times;
            </Button>
          </div>
        ))}
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={handleAddColor}
          disabled={disabled}
          className="w-full"
        >
          {buttonText}
        </Button>
      </div>
    </div>
  );
}

export default ColorListEditor;
