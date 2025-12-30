import { Input } from '@/components/ui/input';

interface StringFieldEditorProps {
  /** Current value of the field */
  value: string;
  /** Callback when value changes */
  onChange: (value: string) => void;
  /** Label text displayed above the field */
  label: string;
  /** Placeholder text when empty */
  placeholder?: string;
  /** Whether to use textarea for multiline input */
  multiline?: boolean;
  /** Minimum height for multiline textarea (e.g., "80px", "120px") */
  minHeight?: string;
  /** Maximum length for the input */
  maxLength?: number;
  /** Whether the field is disabled */
  disabled?: boolean;
  /** Additional class names for the container */
  className?: string;
  /** Whether the field is required */
  required?: boolean;
}

/**
 * Reusable string field editor component.
 * Supports both single-line (Input) and multi-line (textarea) modes.
 */
export function StringFieldEditor({
  value,
  onChange,
  label,
  placeholder,
  multiline = false,
  minHeight = '80px',
  maxLength,
  disabled = false,
  className = '',
  required = false,
}: StringFieldEditorProps) {
  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>
  ) => {
    onChange(e.target.value);
  };

  const labelElement = (
    <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
      {label}
      {required && <span className="text-destructive ml-1">*</span>}
    </label>
  );

  if (multiline) {
    return (
      <div className={className}>
        {labelElement}
        <textarea
          value={value}
          onChange={handleChange}
          placeholder={placeholder}
          maxLength={maxLength}
          disabled={disabled}
          className="mt-1 w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50 resize-y"
          style={{ minHeight }}
        />
        {maxLength && (
          <div className="text-xs text-muted-foreground mt-1 text-right">
            {value.length}/{maxLength}
          </div>
        )}
      </div>
    );
  }

  return (
    <div className={className}>
      {labelElement}
      <Input
        value={value}
        onChange={handleChange}
        placeholder={placeholder}
        maxLength={maxLength}
        disabled={disabled}
        className="mt-1"
      />
      {maxLength && (
        <div className="text-xs text-muted-foreground mt-1 text-right">
          {value.length}/{maxLength}
        </div>
      )}
    </div>
  );
}

export default StringFieldEditor;
