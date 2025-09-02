import React, { useState, useEffect } from 'react';
import { localStorage as protocolStorage } from '../lib/localStorage';

const ProtocolHistory = ({ onLoadProtocol }) => {
  const [protocols, setProtocols] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const [stats, setStats] = useState(null);

  useEffect(() => {
    loadProtocols();
  }, []);

  const loadProtocols = () => {
    try {
      setLoading(true);
      const data = protocolStorage.getAllProtocols();
      const storageStats = protocolStorage.getStorageStats();
      setProtocols(data);
      setStats(storageStats);
    } catch (error) {
      setError('Ошибка загрузки протоколов: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = (protocolId) => {
    if (!window.confirm('Удалить этот протокол из локального хранилища?')) return;

    try {
      protocolStorage.deleteProtocol(protocolId);
      loadProtocols(); // Refresh the list
    } catch (error) {
      setError('Ошибка удаления: ' + error.message);
    }
  };

  const handleLoad = (protocol) => {
    onLoadProtocol({
      filename: protocol.filename,
      document_summary: protocol.document_summary,
      analysis_results: protocol.analysis_results
    });
  };

  const handleClearAll = () => {
    if (!window.confirm('Удалить ВСЕ сохраненные протоколы? Это действие нельзя отменить.')) return;
    
    try {
      protocolStorage.clearAll();
      loadProtocols();
    } catch (error) {
      setError('Ошибка очистки: ' + error.message);
    }
  };

  const filteredProtocols = searchTerm 
    ? protocolStorage.searchProtocols(searchTerm)
    : protocols;

  if (loading) {
    return (
      <div className="glass-card">
        <div className="loading-container">
          <div className="loading-spinner"></div>
          <div className="loading-text">Загрузка истории протоколов...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="glass-card">
      <div className="protocol-history-header">
        <h3>📚 История анализов</h3>
        <div className="search-container">
          <input
            type="text"
            placeholder="Поиск по названию файла или содержанию..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="search-input"
          />
        </div>
        {protocols.length > 0 && (
          <button 
            onClick={handleClearAll}
            className="clear-all-btn"
            title="Очистить все сохраненные протоколы"
          >
            🗑️ Очистить все
          </button>
        )}
      </div>

      {stats && (
        <div className="storage-stats">
          <div className="stat-item">
            <span className="stat-icon">📋</span>
            <span className="stat-value">{stats.totalProtocols}</span>
            <span className="stat-label">протоколов</span>
          </div>
          <div className="stat-item">
            <span className="stat-icon">💊</span>
            <span className="stat-value">{stats.totalDrugs}</span>
            <span className="stat-label">препаратов</span>
          </div>
          <div className="stat-item">
            <span className="stat-icon">💾</span>
            <span className="stat-value">{(stats.storageSize / 1024).toFixed(1)} КБ</span>
            <span className="stat-label">данных</span>
          </div>
        </div>
      )}

      {error && <div className="error-message">{error}</div>}

      {filteredProtocols.length === 0 ? (
        <div className="empty-state">
          <div className="medical-icon">📋</div>
          <h4>{searchTerm ? 'Ничего не найдено' : 'Нет сохраненных протоколов'}</h4>
          <p>{searchTerm ? 'Попробуйте изменить поисковый запрос' : 'Загрузите и проанализируйте первый протокол'}</p>
        </div>
      ) : (
        <div className="protocols-list">
          {filteredProtocols.map((protocol) => (
            <div key={protocol.id} className="protocol-item">
              <div className="protocol-info">
                <div className="protocol-filename">
                  📄 {protocol.filename}
                </div>
                <div className="protocol-meta">
                  <span className="protocol-date">
                    📅 {new Date(protocol.upload_date).toLocaleDateString('ru-RU')}
                  </span>
                  <span className="protocol-drugs-count">
                    💊 {protocol.analysis_results?.length || 0} препаратов
                  </span>
                </div>
                {protocol.document_summary && (
                  <div className="protocol-summary">
                    {protocol.document_summary.substring(0, 150)}
                    {protocol.document_summary.length > 150 ? '...' : ''}
                  </div>
                )}
              </div>
              <div className="protocol-actions">
                <button
                  onClick={() => handleLoad(protocol)}
                  className="action-btn load-btn"
                  title="Загрузить результаты анализа"
                >
                  📊 Загрузить
                </button>
                <button
                  onClick={() => handleDelete(protocol.id)}
                  className="action-btn delete-btn"
                  title="Удалить протокол"
                >
                  🗑️
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default ProtocolHistory;