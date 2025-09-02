import React, { useState, useEffect } from 'react';
import { protocolStorage } from '../lib/supabase';

const ProtocolHistory = ({ onLoadProtocol }) => {
  const [protocols, setProtocols] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    loadProtocols();
  }, []);

  const loadProtocols = async () => {
    try {
      setLoading(true);
      const data = await protocolStorage.getUserProtocols();
      setProtocols(data);
    } catch (error) {
      setError('Ошибка загрузки протоколов: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (protocolId) => {
    if (!window.confirm('Удалить этот протокол?')) return;

    try {
      await protocolStorage.deleteProtocol(protocolId);
      setProtocols(protocols.filter(p => p.id !== protocolId));
    } catch (error) {
      setError('Ошибка удаления: ' + error.message);
    }
  };

  const handleLoad = async (protocol) => {
    try {
      const fullProtocol = await protocolStorage.getProtocol(protocol.id);
      onLoadProtocol({
        filename: fullProtocol.filename,
        document_summary: fullProtocol.document_summary,
        analysis_results: fullProtocol.analysis_results
      });
    } catch (error) {
      setError('Ошибка загрузки протокола: ' + error.message);
    }
  };

  const filteredProtocols = protocols.filter(protocol =>
    protocol.filename.toLowerCase().includes(searchTerm.toLowerCase()) ||
    (protocol.document_summary && protocol.document_summary.toLowerCase().includes(searchTerm.toLowerCase()))
  );

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
      </div>

      {error && <div className="error-message">{error}</div>}
      }

      {filteredProtocols.length === 0 ? (
        <div className="empty-state">
          <div className="medical-icon">📋</div>
          <h4>Нет сохраненных протоколов</h4>
          <p>Загрузите и проанализируйте первый протокол</p>
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
                    {new Date(protocol.upload_date).toLocaleDateString('ru-RU')}
                  </span>
                  <span className="protocol-drugs-count">
                    {protocol.analysis_results?.length || 0} препаратов
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