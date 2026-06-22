import type { SelectHTMLAttributes } from "react";
import { ChevronDown } from "lucide-react";
import { selectCls } from "./formStyles";

// A native <select> wearing the shared Orionfold field styling with a custom down-chevron.
// The native arrow is hidden (it varies per-OS and sits flush at the edge); we draw a lucide
// chevron with breathing room so every dropdown on the setup surface reads identically.
// `className` sizes the FIELD (the wrapper): the <select> always fills it, so the chevron —
// positioned against the wrapper's right edge — stays flush with the control at any width.
// Default (no className) = a full-width block, matching a select dropped into a grid/label column.
export function SelectField({
  className = "",
  children,
  ...props
}: SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <div className={className ? `relative ${className}` : "relative"}>
      <select {...props} className={selectCls}>
        {children}
      </select>
      <ChevronDown
        aria-hidden
        className="pointer-events-none absolute right-3 top-1/2 size-4 -translate-y-1/2 text-(--color-ink-muted)"
      />
    </div>
  );
}
