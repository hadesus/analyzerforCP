import React, { useState, useMemo } from 'react';
import './App.css';
import { localStorage as protocolStorage } from './lib/localStorage';
import ProtocolHistory from './components/ProtocolHistory';
import FileUpload from './components/FileUpload';
import ResultsTable from './components/ResultsTable';
import ExportButtons from './components/ExportButtons';
import LoadingIndicator from './components/LoadingIndicator';
import ErrorMessage from './components/ErrorMessage';

const useSortableData = (items, config = null) => {
  const [sortConfig, setSortConfig] = useState(config);

  const sortedItems = useMemo(() => {
    if (!items || !Array.isArray(items)) return [];
    let sortableItems = [...items];
    if (sortConfig !== null) {
      sortableItems.sort((a, b) => {
        const getNestedValue = (obj, path) => path.split('.').reduce((o, k) => (o || {})[k], obj);
        const aValue = getNestedValue(a, sortConfig.key);
        const bValue = getNestedValue(b, sortConfig.key);
        if (aValue < bValue) {
          return sortConfig.direction === 'ascending' ? -1 : 1;
        }
        if (aValue > bValue) {
          return sortConfig.direction === 'ascending' ? 1 : -1;
        }
        return 0;
      });
    }
    return sortableItems;
  }, [items, sortConfig]);

  const requestSort = (key) => {
    let direction = 'ascending';
    if (sortConfig && sortConfig.key === key && sortConfig.direction === 'ascending') {
      direction = 'descending';
    }
    setSortConfig({ key, direction });
  };

  return { items: sortedItems || [], requestSort, sortConfig };
};

function App() {
  const [showHistory, setShowHistory] = useState(false);
  const [analysisData, setAnalysisData] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [filterText, setFilterText] = useState('');
  const [currentStage, setCurrentStage] = useState('parsing');
  const [progress, setProgress] = useState(0);

  const analysisResults = analysisData?.analysis_results || [];
  const documentSummary = analysisData?.document_summary;

  const { items: sortedResults, requestSort, sortConfig } = useSortableData(analysisResults);

  const filteredResults = useMemo(() => {
    if (!sortedResults || !Array.isArray(sortedResults)) return [];
    if (!filterText) return sortedResults;

    return sortedResults.filter(item => {
        const sourceName = item.source_data?.drug_name_source?.toLowerCase() || '';
        const innName = item.normalization?.inn_name?.toLowerCase() || '';
        return sourceName.includes(filterText.toLowerCase()) || innName.includes(filterText.toLowerCase());
    });
  }, [sortedResults, filterText]);

  const handleAnalysisSuccess = (data) => {
    setAnalysisData(data);
    
    // Save to local storage
    if (data.analysis_results?.length > 0) {
      try {
        protocolStorage.saveProtocol(
          data.filename,
          data.document_summary,
          data.analysis_results
        );
        console.log('✅ Protocol saved to local storage');
      } catch (error) {
        console.error('❌ Error saving protocol:', error);
        // Don't show error to user, just log it
      }
    }
  };

  const handleLoadProtocol = (protocolData) => {
    setAnalysisData(protocolData);
    setShowHistory(false);
  };

  return (
    <div className="App">
      <div className="medical-decoration dna">🧬</div>
      <div className="medical-decoration molecule">⚛️</div>
      <div className="medical-decoration microscope">🔬</div>
      
      <header className="App-header">
        <h1>Анализатор Клинических Протоколов</h1>
        <p className="subtitle">Профессиональный анализ медицинских документов с использованием NLP и LLM</p>
        <div className="features">
          <div className="feature-badge">
            <span>🤖</span>
            <span>Единый AI Анализ</span>
          </div>
          <div className="feature-badge">
            <span>🏥</span>
            <span>Регуляторные Проверки</span>
          </div>
          <div className="feature-badge">
            <span>📊</span>
            <span>GRADE Оценка</span>
          </div>
          <div className="feature-badge">
            <span>📚</span>
            <span>PubMed Интеграция</span>
          </div>
        </div>
        
        <div className="header-actions">
          <button 
            className="history-btn"
            onClick={() => setShowHistory(!showHistory)}
          >
            📚 {showHistory ? 'Скрыть историю' : 'История анализов'}
          </button>
        </div>
      </header>
      
      <main>
        {showHistory && (
          <ProtocolHistory onLoadProtocol={handleLoadProtocol} />
        )}
        
        <div className="glass-card">
          <FileUpload
            onUploadSuccess={handleAnalysisSuccess}
            setIsLoading={setIsLoading}
            setErrorMessage={setErrorMessage}
            setCurrentStage={setCurrentStage}
            setProgress={setProgress}
          />
        </div>
        
        {isLoading && <LoadingIndicator currentStage={currentStage} progress={progress} />}
        {errorMessage && <ErrorMessage message={errorMessage} />}

        {analysisData && (
          <div className="results-container fade-in-up">
            {documentSummary && (
              <div className="summary-container">
                <h3>Общее резюме документа</h3>
                <p>{documentSummary}</p>
              </div>
            )}
            
            <div className="filter-container">
              <div className="filter-icon">🔍</div>
              <input
                type="text"
                className="filter-input"
                placeholder="Поиск по названию препарата или МНН..."
                value={filterText}
                onChange={(e) => setFilterText(e.target.value)}
              />
            </div>
            
            <ExportButtons results={filteredResults} />
            
            <div className="table-container">
              <ResultsTable
                results={filteredResults}
                requestSort={requestSort}
                sortConfig={sortConfig}
              />
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;