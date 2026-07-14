import './LinkListEditor.css';

export interface DraftLink {
  label: string;
  url: string;
  link_type?: string;
}

interface LinkListEditorProps {
  links: DraftLink[];
  onChange: (links: DraftLink[]) => void;
}

/**
 * Repeatable list of external links (a title + URL per row) for the suggestion
 * forms. Purely controlled: the parent owns the array. Empty rows are allowed
 * here and pruned by the parent on submit.
 */
export default function LinkListEditor({ links, onChange }: LinkListEditorProps) {
  const update = (index: number, patch: Partial<DraftLink>) =>
    onChange(links.map((link, i) => (i === index ? { ...link, ...patch } : link)));

  const remove = (index: number) => onChange(links.filter((_, i) => i !== index));

  const add = () => onChange([...links, { label: '', url: '' }]);

  return (
    <div className="link-editor">
      {links.map((link, i) => (
        <div key={i} className="link-editor-row">
          <input
            type="text"
            className="link-editor-input link-editor-label"
            value={link.label}
            onChange={(e) => update(i, { label: e.target.value })}
            placeholder="Link title (e.g. Publisher)"
            aria-label="Link title"
          />
          <input
            type="url"
            className="link-editor-input link-editor-url"
            value={link.url}
            onChange={(e) => update(i, { url: e.target.value })}
            placeholder="https://…"
            aria-label="Link URL"
          />
          <button
            type="button"
            className="link-editor-remove"
            onClick={() => remove(i)}
            aria-label="Remove link"
            title="Remove link"
          >
            ×
          </button>
        </div>
      ))}
      <button type="button" className="link-editor-add" onClick={add}>
        + Add link
      </button>
    </div>
  );
}
