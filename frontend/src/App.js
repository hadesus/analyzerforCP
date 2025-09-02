import React, { useState, useMemo } from 'react';
import './App.css';
import FileUpload from './components/FileUpload';
import ResultsTable from './components/ResultsTable';
import ExportButtons from './components/ExportButtons';

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
      <header className="App-header">
        <h1>Анализатор Клинических Протоколов</h1>
      </header>
      <main>
        <FileUpload
          onUploadSuccess={setAnalysisData}
          setIsLoading={setIsLoading}
          setErrorMessage={setErrorMessage}
        />
        {isLoading && <div className="loading-indicator">Анализ документа... Это может занять несколько минут.</div>}
        {errorMessage && <div className="error-message">{errorMessage}</div>}

        {analysisData && (
          <div className="results-container">
            {documentSummary && (
              <div className="summary-container">
                <h3>Общее резюме документа</h3>
                <p>{documentSummary}</p>
              </div>
            )}
            <input
              type="text"
              placeholder="Фильтр по названию или МНН..."
              value={filterText}
              onChange={(e) => setFilterText(e.target.value)}
              style={{ width: '100%', padding: '10px', margin: '20px 0', boxSizing: 'border-box' }}
            />
            <ExportButtons results={filteredResults} />
            <ResultsTable
              results={filteredResults}
              requestSort={requestSort}
              sortConfig={sortConfig}
            />
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
