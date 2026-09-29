type Props = {
  onSuggestion: (text: string) => void;
};

const SUGGESTIONS = [
  {
    label: "Find similar buyers",
    text: "Find buyers in India for motorcycles with high shipping volume",
  },
  {
    label: "Match a company",
    text: "Search companies in India with HS code 8711 that trade with Singapore",
  },
];

export default function ChatEmptyState({ onSuggestion }: Props) {
  return (
    <div className="atlas-empty">
      <h2>How can Atlas help you today?</h2>
      <p>Find new leads, search your contacts and companies.</p>
      <div className="atlas-suggestion-row">
        {SUGGESTIONS.map((item) => (
          <button
            key={item.label}
            type="button"
            className="atlas-chip"
            onClick={() => onSuggestion(item.text)}
          >
            {item.label}
          </button>
        ))}
      </div>
    </div>
  );
}
