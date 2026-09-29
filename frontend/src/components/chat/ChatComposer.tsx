import { FormEvent } from "react";

type Props = {
  value: string;
  busy: boolean;
  onChange: (value: string) => void;
  onSubmit: (event: FormEvent) => void;
  showChips?: boolean;
  onChip?: (text: string) => void;
};

const CHIPS = [
  {
    label: "Find similar buyers",
    text: "Find buyers in India for motorcycles with high shipping volume",
  },
  {
    label: "Match a company",
    text: "Search companies in India with HS code 8711 that trade with Singapore",
  },
];

export default function ChatComposer({
  value,
  busy,
  onChange,
  onSubmit,
  showChips = false,
  onChip,
}: Props) {
  return (
    <div className="atlas-composer-wrap">
      <form className="atlas-composer" onSubmit={onSubmit}>
        <input
          value={value}
          onChange={(event) => onChange(event.target.value)}
          placeholder="Ask Atlas to find similar buyers or suppliers..."
          disabled={busy}
        />
        <button
          type="submit"
          className="atlas-send"
          disabled={busy || !value.trim()}
          aria-label="Send"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor" aria-hidden>
            <path d="M12 4l-1.41 1.41L16.17 11H4v2h12.17l-5.58 5.59L12 20l8-8-8-8z" />
          </svg>
        </button>
      </form>
      {showChips && onChip && (
        <div className="atlas-suggestion-row under-composer">
          {CHIPS.map((item) => (
            <button
              key={item.label}
              type="button"
              className="atlas-chip"
              onClick={() => onChip(item.text)}
              disabled={busy}
            >
              {item.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
