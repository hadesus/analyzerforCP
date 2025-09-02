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

  const renderDetails = (item) => (
    <div className="details-content">
      <div className="details-grid">
        <div className="detail-section">
          <h5>🔬 Нормализация препарата</h5>
          <div className="data-card">
            <div className="data-label">МНН (Источник)</div>
            <div className="data-value">{item.normalization?.inn_name || 'Не определено'} ({item.normalization?.source || 'Неизвестно'})</div>
          </div>
          <div className="data-card">
            <div className="data-label">Уровень уверенности</div>
            <div className="data-value">{item.normalization?.confidence || 'Не указан'}</div>
          </div>
        </div>

        <div className="detail-section">
          <h5>🏛️ Регуляторные проверки</h5>
          <div className="regulatory-grid">
            <div className="regulatory-item">
              <div className="label">FDA</div>
              <StatusBadge status={item.regulatory_checks?.regulatory_checks?.FDA?.status} />
            </div>
            <div className="regulatory-item">
              <div className="label">EMA</div>
              <StatusBadge status={item.regulatory_checks?.regulatory_checks?.EMA?.status} />
            </div>
            <div className="regulatory-item">
              <div className="label">BNF</div>
              <StatusBadge status={item.regulatory_checks?.regulatory_checks?.BNF?.status} />
            </div>
            <div className="regulatory-item">
              <div className="label">WHO EML</div>
              <StatusBadge status={item.regulatory_checks?.regulatory_checks?.WHO_EML?.status} />
            </div>
          </div>
          
          {item.regulatory_checks?.dosage_check && (
            <div className="data-card" style={{ marginTop: 'var(--space-lg)' }}>
              <div className="data-label">💊 Сравнение дозировки</div>
              <StatusBadge 
                status={item.regulatory_checks.dosage_check.comparison_result} 
                isDosage={true} 
              />
            </div>
          )}
        </div>

        <div className="detail-section">
          <h5>📚 Исследования PubMed</h5>
          {item.pubmed_articles && item.pubmed_articles.length > 0 ? (
            <ul className="pubmed-list">
              {item.pubmed_articles.map((article, idx) => (
                <li key={idx} className="pubmed-item">
                  <a href={article.link} target="_blank" rel="noopener noreferrer">
                    {article.title}
                  </a>
                  <div className="pubmed-meta">
                    {article.journal} • {article.publication_date}
                  </div>
                </li>
              ))}
            </ul>
          ) : (
            <p style={{ color: 'var(--neutral-500)', fontStyle: 'italic' }}>
              Исследования не найдены
            </p>
          )}
        </div>

        <div className="detail-section">
          <h5>📊 Детальный анализ</h5>
          <div className="data-card">
            <div className="data-label">Обоснование GRADE</div>
            <div className="data-value">{item.ai_analysis?.ud_ai_justification || 'Не предоставлено'}</div>
          </div>
          <div className="data-card">
            <div className="data-label">Исходные данные</div>
            <div className="data-value">
              <strong>Дозировка:</strong> {item.source_data?.dosage_source || 'Не указано'}<br/>
              <strong>Путь введения:</strong> {item.source_data?.route_source || 'Не указано'}<br/>
              <strong>Контекст:</strong> {item.source_data?.context_indication || 'Не указан'}
            </div>
          </div>
        </div>
      </div>
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
            📊 GRADE Анализ{getSortIndicator('ai_analysis.ud_ai_grade')}
          </th>
          <th>📝 Заметка анализа</th>
        </tr>
      </thead>
      <tbody>
        {results.map((item, index) => (
          <React.Fragment key={index}>
            <tr 
              onClick={() => handleRowClick(index)}
              className={expandedRow === index ? 'expanded' : ''}
            >
              <td>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                  <strong>{item.source_data?.drug_name_source || 'Не указано'}</strong>
                  <small style={{ color: 'var(--neutral-500)', fontFamily: 'JetBrains Mono' }}>
                    Нажмите для деталей
                  </small>
                </div>
              </td>
              <td>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                  <strong>{item.normalization?.inn_name || 'Не определено'}</strong>
                  <small style={{ color: 'var(--neutral-500)', fontFamily: 'JetBrains Mono' }}>
                    Источник: {item.normalization?.source || 'Неизвестно'}
                  </small>
                </div>
              </td>
              <td>
                <div style={{ fontFamily: 'JetBrains Mono', fontSize: '0.9rem' }}>
                  {item.source_data?.dosage_source || 'Не указано'}
                </div>
              </td>
              <td>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                  <GradeBadge grade={item.ai_analysis?.ud_ai_grade} />
                  <div style={{ fontSize: '0.8rem', color: 'var(--neutral-600)', fontStyle: 'italic' }}>
                    {item.ai_analysis?.ud_ai_justification}
                  </div>
                </div>
              </td>
              <td>
                <div style={{ fontSize: '0.9rem', lineHeight: '1.5' }}>
                  {item.ai_analysis?.ai_summary_note || 'Заметка не сгенерирована'}
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