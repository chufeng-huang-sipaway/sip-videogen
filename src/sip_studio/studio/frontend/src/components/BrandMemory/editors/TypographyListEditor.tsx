import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import type { TypographyRule } from '@/types/brand-identity';

interface TypographyListEditorProps {
  /** Current list of typography rules */
  value: TypographyRule[];
  /** Callback when list changes */
  onChange: (value: TypographyRule[]) => void;
  /** Label text displayed above the list */
  label: string;
  /** Whether inputs are disabled */
  disabled?: boolean;
  /** Minimum number of items required (prevents removal below this count) */
  minItems?: number;
  /** Custom text for add button (defaults to "Add Typography Rule") */
  addButtonText?: string;
  /** Additional class names for the container */
  className?: string;
}

/**
 * Reusable typography list editor component.
 * Displays a list of typography rules with role, family, weight, and style_notes fields.
 * Supports add/remove functionality.
 *
 * Used for editing the typography array in VisualIdentity.
 */
export function TypographyListEditor({
  value,
  onChange,
  label,
  disabled = false,
  minItems = 0,
  addButtonText,
  className = '',
}: TypographyListEditorProps) {
  const handleFieldChange = (
    index: number,
    field: keyof TypographyRule,
    newValue: string
  ) => {
    const newList = [...value];
    newList[index] = { ...newList[index], [field]: newValue };
    onChange(newList);
  };

  const handleAddRule = () => {
    const newRule: TypographyRule = {
      role: '',
      family: '',
      weight: '',
      style_notes: '',
    };
    onChange([...value, newRule]);
  };

  const handleRemoveRule = (index: number) => {
    const newList = value.filter((_, i) => i !== index);
    onChange(newList);
  };

  // Default add button text
  const buttonText = addButtonText ?? '+ Add Typography Rule';

  return (
    <div className={className}>
      <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
        {label}
      </label>
      <div className="mt-1 space-y-3">
        {value.map((rule, index) => (
          <div
            key={index}
            className="border border-border rounded-md p-3 space-y-2 bg-muted/30"
          >
            <div className="flex justify-between items-center">
              <span className="text-xs text-muted-foreground">
                Rule {index + 1}
              </span>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => handleRemoveRule(index)}
                disabled={disabled || value.length <= minItems}
                className="px-2 h-6 text-muted-foreground hover:text-destructive"
              >
                &times;
              </Button>
            </div>
            {/* Role and Family row */}
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="text-xs text-muted-foreground">Role</label>
                <Input
                  value={rule.role}
                  onChange={(e) =>
                    handleFieldChange(index, 'role', e.target.value)
                  }
                  disabled={disabled}
                  placeholder="e.g., Headings, Body Text"
                  className="mt-1"
                />
              </div>
              <div>
                <label className="text-xs text-muted-foreground">
                  Font Family
                </label>
                <Input
                  value={rule.family}
                  onChange={(e) =>
                    handleFieldChange(index, 'family', e.target.value)
                  }
                  disabled={disabled}
                  placeholder="e.g., Inter, Roboto"
                  className="mt-1"
                />
              </div>
            </div>
            {/* Weight row */}
            <div>
              <label className="text-xs text-muted-foreground">Weight</label>
              <Input
                value={rule.weight}
                onChange={(e) =>
                  handleFieldChange(index, 'weight', e.target.value)
                }
                disabled={disabled}
                placeholder="e.g., 400, 600, Bold"
                className="mt-1"
              />
            </div>
            {/* Style Notes row */}
            <div>
              <label className="text-xs text-muted-foreground">
                Style Notes
              </label>
              <textarea
                value={rule.style_notes}
                onChange={(e) =>
                  handleFieldChange(index, 'style_notes', e.target.value)
                }
                disabled={disabled}
                placeholder="Additional styling notes..."
                className="mt-1 w-full min-h-[60px] rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50 resize-none"
              />
            </div>
          </div>
        ))}
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={handleAddRule}
          disabled={disabled}
          className="w-full"
        >
          {buttonText}
        </Button>
      </div>
    </div>
  );
}

export default TypographyListEditor;
