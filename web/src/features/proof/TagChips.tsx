import { tagToken } from "./tags";

// Domain tags as categorical chips — squared, value-token colors, never interactive.
export function TagChips({ tags }: { tags: string[] }) {
  if (tags.length === 0) return null;
  return (
    <div className="flex flex-wrap gap-1.5">
      {tags.map((t) => (
        <span key={t} className={`of-tag of-tag--${tagToken(t)}`}>
          {t}
        </span>
      ))}
    </div>
  );
}
