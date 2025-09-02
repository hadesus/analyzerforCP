import React, { useState, useMemo } from 'react';
import './App.css';
import FileUpload from './components/FileUpload';
import ResultsTable from './components/ResultsTable';
import ExportButtons from './components/ExportButtons';
import LoadingIndicator from './components/LoadingIndicator';
import ErrorMessage from './components/ErrorMessage';

const useSortableData = (items, config = null) => {
  const [sortConfig, setSortConfig] = useState(config);

  const sortedItems = useMemo(() => {
    if (!items) return null;
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

  return { items: sortedItems, requestSort, sortConfig };
};

function App() {
  const [analysisData, setAnalysisData] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [filterText, setFilterText] = useState('');

  const analysisResults = analysisData?.analysis_results;
  const documentSummary = analysisData?.document_summary;

  const { items: sortedResults, requestSort, sortConfig } = useSortableData(analysisResults);

  const filteredResults = useMemo(() => {
    if (!sortedResults) return null;
    if (!filterText) return sortedResults;

    return sortedResults.filter(item => {
        const sourceName = item.source_data?.drug_name_source?.toLowerCase() || '';
        const innName = item.normalization?.inn_name?.toLowerCase() || '';
        return sourceName.includes(filterText.toLowerCase()) || innName.includes(filterText.toLowerCase());
    });
  }, [sortedResults, filterText]);

  return (
    <div className="App">
      <div className="medical-pattern"></div>
      <header className="App-header">
        <h1>Анализатор Клинических Протоколов</h1>
        <p className="subtitle">Профессиональный анализ медицинских документов с использованием ИИ</p>
      </header>
      <main>
        <div className="glass-card">
          <FileUpload
            onUploadSuccess={setAnalysisData}
            setIsLoading={setIsLoading}
            setErrorMessage={setErrorMessage}
          />
        </div>
        
        {isLoading && <LoadingIndicator />}
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
