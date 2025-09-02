import React, { useState } from 'react';

import StatusBadge from './StatusBadge';
import GradeBadge from './GradeBadge';

const ResultsTable = ({ results, requestSort, sortConfig }) => {
  const [expandedRow, setExpandedRow] = useState(null);

  if (!results || results.length === 0) {
    return (
      <div className="glass-card" style={{ textAlign: 'center', padding: '3rem' }}>
        <div className="medical-icon" style={{ margin: '0 auto 1rem', fontSize: '3rem' }}>🔍</div>
        <h3 style={{ color: 'var(--neutral-600)', marginBottom: '0.5rem' }}>Нет данных для отображения</h3>
        <p style={{ color: 'var(--neutral-500)' }}>По вашему фильтру ничего не найдено или данные не загружены</p>
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
        <h4>Детальная информация</h4>
        <p><strong>МНН (Источник):</strong> {item.normalization.inn_name} ({item.normalization.source})</p>
        <p><strong>Уровень док-ти (Источник):</strong> {item.source_data.evidence_level_source || 'Не указан'}</p>
        <hr />
        <h4>Проверки по регуляторам:</h4>
        {renderDetailValue(item.regulatory_checks)}
        <hr />
        <h4>Найденные исследования (PubMed):</h4>
        {item.pubmed_articles && item.pubmed_articles.length > 0 ? (
            <ul>
                {item.pubmed_articles.map(article => (
                    <li key={article.pmid}>
                        <a href={article.link} target="_blank" rel="noopener noreferrer">
                            {article.title}
                        </a> ({article.journal}, {article.publication_date})
                    </li>
                ))}
            </ul>
        ) : <p>Исследования не найдены.</p>}
        }
    </div>
  );

  return (
    <table className="results-table">
      <thead>
        <tr>
          <th onClick={() => requestSort('source_data.drug_name_source')}>
            Название (Источник){getSortIndicator('source_data.drug_name_source')}
          </th>
          <th onClick={() => requestSort('normalization.inn_name')}>
            МНН{getSortIndicator('normalization.inn_name')}
          </th>
          <th onClick={() => requestSort('source_data.dosage_source')}>
            Дозировка (Источник){getSortIndicator('source_data.dosage_source')}
          </th>
          <th onClick={() => requestSort('ai_analysis.ud_ai_grade')}>
            🧠 GRADE Анализ{getSortIndicator('ai_analysis.ud_ai_grade')}
          </th>
          <th>📝 Заметка ИИ</th>
        </tr>
      </thead>
      <tbody>
        {results.map((item, index) => (
          <React.Fragment key={index}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                  <strong>{item.normalization?.inn_name || 'Не определено'}</strong>
                  <small style={{ color: 'var(--neutral-500)', fontFamily: 'JetBrains Mono' }}>
                    Источник: {item.normalization?.source || 'Неизвестно'}
                  </small>
                </div>
              <td>{item.source_data.drug_name_source}</td>
              <td>{item.normalization.inn_name || 'Не определено'}</td>
                <div style={{ fontFamily: 'JetBrains Mono', fontSize: '0.9rem' }}>
                  {item.source_data.dosage_source || 'Не указано'}
                </div>
              <td>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <GradeBadge grade={item.ai_analysis?.ud_ai_grade} />
                <div style={{ fontSize: '0.8rem', color: 'var(--neutral-600)', marginTop: '0.5rem', fontStyle: 'italic' }}>
                  {item.ai_analysis?.ud_ai_justification}
                </div>
                  <strong>{item.source_data.drug_name_source}</strong>
                </div>
                <div style={{ fontSize: '0.9rem', lineHeight: '1.5' }}>
                  {item.ai_analysis?.ai_summary_note || 'Заметка не сгенерирована'}
                </div>
              <td>{item.ai_analysis.ai_summary_note}</td>
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
