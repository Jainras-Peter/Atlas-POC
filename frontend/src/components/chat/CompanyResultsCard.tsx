import type { CompanyHit } from "../../types";

type Props = {
  companies: CompanyHit[];
  onSelect?: (companyId: string) => void;
};

export default function CompanyResultsCard({ companies, onSelect }: Props) {
  if (!companies.length) return null;
  return (
    <div className="atlas-result-card">
      <div className="atlas-result-title">Companies ({companies.length})</div>
      <div className="atlas-result-list">
        {companies.map((company) => (
          <button
            key={company.companyId}
            type="button"
            className="atlas-result-row"
            onClick={() => onSelect?.(company.companyId)}
          >
            <div className="atlas-result-main">
              <strong>{company.name}</strong>
              <span className="mono">{company.companyId}</span>
            </div>
            <div className="atlas-result-meta">
              {[company.city, company.country].filter(Boolean).join(", ")}
              {company.role ? ` · ${company.role}` : ""}
              {company.matchScore != null ? ` · score ${company.matchScore}` : ""}
            </div>
            {company.products && company.products.length > 0 && (
              <div className="atlas-result-tags">
                {company.products.slice(0, 4).map((p) => (
                  <span key={p} className="atlas-tag">
                    {p}
                  </span>
                ))}
              </div>
            )}
          </button>
        ))}
      </div>
      {onSelect && (
        <p className="atlas-result-hint">Click a company to lock it and see full details.</p>
      )}
    </div>
  );
}
