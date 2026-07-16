import './InstrumentationChips.css';

interface InstrumentationChipsProps {
  /** Canonical category names currently selected. */
  selected: string[];
  onChange: (selected: string[]) => void;
  /** The full canonical vocabulary, from useInstrumentations(). */
  options: string[];
  /** The work's primary category — shown as fixed context, never selectable. */
  primary?: string | null;
}

/**
 * Multi-select for a work's *additional* playable instrumentations.
 *
 * Chips rather than a LinkListEditor-style repeatable row editor: instrumentation is
 * a closed 33-item vocabulary, so free text would only invite typos that the backend
 * would then silently drop. The primary is rendered as a fixed chip for context —
 * it's what the work *is*, and offering it as an "alternate" is meaningless.
 */
export default function InstrumentationChips({
  selected, onChange, options, primary,
}: InstrumentationChipsProps) {
  const toggle = (name: string) =>
    onChange(
      selected.includes(name)
        ? selected.filter((n) => n !== name)
        : [...selected, name]
    );

  const selectable = options.filter((name) => name !== primary);

  return (
    <div className="instrumentation-chips">
      {primary && (
        <p className="instrumentation-chips-primary">
          Written for <strong>{primary}</strong>. Select any other way it can be played:
        </p>
      )}
      <div className="instrumentation-chips-list" role="group" aria-label="Also playable as">
        {selectable.map((name) => {
          const active = selected.includes(name);
          return (
            <button
              key={name}
              type="button"
              className={`instrumentation-chip${active ? ' instrumentation-chip--active' : ''}`}
              aria-pressed={active}
              onClick={() => toggle(name)}
            >
              {name}
            </button>
          );
        })}
      </div>
    </div>
  );
}
