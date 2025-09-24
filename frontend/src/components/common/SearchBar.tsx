import type { InputHTMLAttributes, ReactNode } from "react";

import { cn } from "@/lib/utils";

export interface SearchBarProps {
  id: string;
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  className?: string;
  inputClassName?: string;
  inputProps?: Omit<InputHTMLAttributes<HTMLInputElement>, "id" | "value" | "onChange">;
  inputRef?: React.Ref<HTMLInputElement>;
  children?: ReactNode;
}

export function SearchBar({
  id,
  label,
  value,
  onChange,
  placeholder,
  className,
  inputClassName,
  inputProps,
  inputRef,
  children,
}: SearchBarProps) {
  return (
    <div className={cn("grid gap-2", className)}>
      <label className="text-sm font-medium" htmlFor={id}>
        {label}
      </label>
      <div className="space-y-2">
        <input
          {...inputProps}
          autoComplete={inputProps?.autoComplete ?? "off"}
          className={cn(
            "h-10 rounded-md border border-input bg-background px-3 text-sm shadow-sm",
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
            inputClassName,
          )}
          id={id}
          ref={inputRef}
          onChange={event => onChange(event.target.value)}
          placeholder={placeholder}
          type={inputProps?.type ?? "search"}
          value={value}
        />
        {children}
      </div>
    </div>
  );
}
