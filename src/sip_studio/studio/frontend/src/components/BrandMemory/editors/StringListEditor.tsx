import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

interface StringListEditorProps {
  /** Current list of string values */
  value: string[];
  /** Callback when list changes */
  onChange: (value: string[]) => void;
  /** Label text displayed above the list */
  label: string;
  /** Placeholder text for each input */
  placeholder?: string;
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
 * Reusable string list editor component.
 * Displays a list of string inputs with add/remove functionality.
 *
 * Used for editing arrays of strings like brand values, key messages,
 * tone attributes, competitors, etc.
 */
export function StringListEditor({
  value,
  onChange,
  label,
  placeholder,
  disabled = false,
  minItems = 0,
  addButtonText,
  className = '',
}: StringListEditorProps) {
  const handleItemChange = (index: number, newValue: string) => {
    const newList = [...value];
    newList[index] = newValue;
    onChange(newList);
  };

  const handleAddItem = () => {
    onChange([...value, '']);
  };

  const handleRemoveItem = (index: number) => {
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
        {value.map((item, index) => (
          <div key={index} className="flex gap-2">
            <Input
              value={item}
              onChange={(e) => handleItemChange(index, e.target.value)}
              placeholder={placeholder}
              disabled={disabled}
              className="flex-1"
            />
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => handleRemoveItem(index)}
              disabled={disabled || value.length <= minItems}
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
          onClick={handleAddItem}
          disabled={disabled}
          className="w-full"
        >
          {buttonText}
        </Button>
      </div>
    </div>
  );
}

export default StringListEditor;
