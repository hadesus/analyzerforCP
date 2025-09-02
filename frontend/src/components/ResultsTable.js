import React, { useState } from 'react';
import StatusBadge from './StatusBadge';
import GradeBadge from './GradeBadge';

const ResultsTable = ({ results, requestSort, sortConfig }) => {
  const [expandedRow, setExpandedRow] = useState(null);

  if (!results || results.length === 0) {
    return (
      <div className="glass-card" style={{ textAlign: 'center', padding: '3rem' }}>
        <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>🔍</div>
        <h3 style={{ color: 'var(--neutral-600)', marginBottom: '0.5rem' }}>Нет данных</h3>
        <p style={{ color: 'var(--neutral-500)' }}>
          Нет данных для отображения или по вашему фильтру ничего не найдено
        </p>
      </div>
    );
  }

  const handleRowClick = (index) => {
    setExpandedRow(expandedRow === index ? null : index);
  };

  const getSortIndicator = (key) => {
    if (!sortConfig || sortConfig.key !== key) {
      return null;
    }
    return sortConfig.direction === 'ascending' ? ' ▲' : ' ▼';
  };

  const renderDetailValue = (value) => {
    if (typeof value === 'object' && value !== null) {
      return <pre>{JSON.stringify(value, null, 2)}</pre>;
    }
    return value;
  }

  const renderDetails = (item) => (
    <div className="details-content">
      <div className="details-grid">
        <div className="detail-section">
          <h5>Основная информация</h5>
          <p><strong>МНН:</strong> {item.normalization.inn_name || 'Не определено'}</p>
          <p><strong>Источник нормализации:</strong> {item.normalization.source}</p>
          <p><strong>Уровень док-ти (Источник):</strong> {item.source_data.evidence_level_source || 'Не указан'}</p>
          <p><strong>Путь введения:</strong> {item.source_data.route_source || 'Не указан'}</p>
          <p><strong>Показания:</strong> {item.source_data.context_indication || 'Не указаны'}</p>
        </div>

        <div className="detail-section">
          <h5>Регуляторные проверки</h5>
          <div className="regulatory-grid">
            <div className="regulatory-item">
              <div className="label">FDA</div>
              <StatusBadge status={item.regulatory_checks?.FDA?.status} />
            </div>
            <div className="regulatory-item">
              <div className="label">EMA</div>
              <StatusBadge status={item.regulatory_checks?.EMA?.status} />
            </div>
            <div className="regulatory-item">
              <div className="label">BNF</div>
              <StatusBadge status={item.regulatory_checks?.BNF?.status} />
            </div>
            <div className="regulatory-item">
              <div className="label">WHO EML</div>
              <StatusBadge status={item.regulatory_checks?.WHO_EML?.status} />
            </div>
          </div>
          {item.dosage_check?.comparison_result && (
            <div style={{ marginTop: '1rem' }}>
              <strong>Сравнение дозировок:</strong>
              <StatusBadge status={item.dosage_check.comparison_result} isDosage={true} />
            </div>
          )}
        </div>

        <div className="detail-section" style={{ gridColumn: '1 / -1' }}>
          <h5>Найденные исследования (PubMed)</h5>
          {item.pubmed_articles && item.pubmed_articles.length > 0 ? (
            <ul className="pubmed-list">
              {item.pubmed_articles.map(article => (
                <li key={article.pmid} className="pubmed-item">
                  <a href={article.link} target="_blank" rel="noopener noreferrer">
                    {article.title}
                  </a>
                  <div className="pubmed-meta">
                    {article.journal} • {article.publication_date} • PMID: {article.pmid}
                  </div>
                </li>
              ))}
            </ul>
          ) : (
            <p style={{ color: 'var(--neutral-500)', fontStyle: 'italic' }}>
              Релевантные исследования не найдены
            </p>
          )}
        </div>
      </div>
    </div>
  );

  return (
    <table className="results-table">
      <thead>
        <tr>
          <th onClick={() => requestSort('source_data.drug_name_source')}>
            Название препарата{getSortIndicator('source_data.drug_name_source')}
          </th>
          <th onClick={() => requestSort('normalization.inn_name')}>
            МНН{getSortIndicator('normalization.inn_name')}
          </th>
          <th onClick={() => requestSort('source_data.dosage_source')}>
            Дозировка{getSortIndicator('source_data.dosage_source')}
          </th>
          <th onClick={() => requestSort('ai_analysis.ud_ai_grade')}>
            Уровень доказательности{getSortIndicator('ai_analysis.ud_ai_grade')}
          </th>
          <th>Заключение ИИ</th>
        </tr>
      </thead>
      <tbody>
        {results.map((item, index) => (
          <React.Fragment key={index}>
            <tr onClick={() => handleRowClick(index)}>
              <td>
                <div style={{ fontWeight: '500', color: 'var(--neutral-800)' }}>
                  {item.source_data.drug_name_source}
                </div>
              </td>
              <td>
                <div style={{ fontWeight: '500', color: 'var(--primary-blue)' }}>
                  {item.normalization.inn_name || 'Не определено'}
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--neutral-500)', marginTop: '0.25rem' }}>
                  {item.normalization.source}
                </div>
              </td>
              <td>
                <code style={{ 
                  background: 'var(--neutral-100)', 
                  padding: '0.25rem 0.5rem', 
                  borderRadius: '6px',
                  fontSize: '0.8rem',
                  fontFamily: 'JetBrains Mono, monospace'
                }}>
                  {item.source_data.dosage_source || 'Не указана'}
                </code>
              </td>
              <td>
                <GradeBadge grade={item.ai_analysis?.ud_ai_grade} />
                <div style={{ 
                  fontSize: '0.75rem', 
                  color: 'var(--neutral-500)', 
                  marginTop: '0.5rem',
                  fontStyle: 'italic'
                }}>
                  {item.ai_analysis?.ud_ai_justification}
                </div>
              </td>
              <td>
                <div style={{ fontSize: '0.875rem', lineHeight: '1.5' }}>
                  {item.ai_analysis?.ai_summary_note}
                </div>
              </td>
            </tr>
            {expandedRow === index && (
              <tr className="details-row">
                <td colSpan="5">{renderDetails(item)}</td>
              </tr>
            )}
          </React.Fragment>
        ))}
      </tbody>
    </table>
  );
};

export default ResultsTable;