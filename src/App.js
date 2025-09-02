import React, { useState, useMemo } from 'react';
import './App.css';
import { supabase, auth, protocolStorage } from './lib/supabase';
import AuthModal from './components/AuthModal';
import UserProfile from './components/UserProfile';
import ProtocolHistory from './components/ProtocolHistory';
import FileUpload from './components/FileUpload';
import ResultsTable from './components/ResultsTable';
import ExportButtons from './components/ExportButtons';
import LoadingIndicator from './components/LoadingIndicator';
import ErrorMessage from './components/ErrorMessage';

function App() {
  const [user, setUser] = useState(null);
  const [authModalOpen, setAuthModalOpen] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [analysisData, setAnalysisData] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [filterText, setFilterText] = useState('');
  const [currentStage, setCurrentStage] = useState('parsing');
  const [progress, setProgress] = useState(0);
  const [authLoading, setAuthLoading] = useState(true);

  // Check authentication status on mount
  React.useEffect(() => {
    const checkAuth = async () => {
      const currentUser = await auth.getUser();
      setUser(currentUser);
      setAuthLoading(false);
    };
    
    checkAuth();
    
    const { data: { subscription } } = auth.onAuthStateChange((event, session) => {
      setUser(session?.user || null);
    });

    return () => subscription.unsubscribe();
  }, []);

  const handleAnalysisSuccess = async (data) => {
    setAnalysisData(data);
    
    // Save to database if user is authenticated
    if (user && data.analysis_results?.length > 0) {
      try {
        await protocolStorage.saveProtocol(
          data.filename,
          data.document_summary,
          data.analysis_results
        );
      } catch (error) {
        console.error('Error saving protocol:', error);
        // Don't show error to user, just log it
      }
    }
  };

  const handleSignOut = async () => {
    await auth.signOut();
    setUser(null);
    setAnalysisData(null);
    setShowHistory(false);
  };

  const handleLoadProtocol = (protocolData) => {
    setAnalysisData(protocolData);
    setShowHistory(false);
  };

  const analysisResults = analysisData?.analysis_results || [];
  const documentSummary = analysisData?.document_summary;

  const sortedResults = useMemo(() => {
    return [...analysisResults].sort((a, b) => {
      const scoreA = parseFloat(a.confidence_score) || 0;
      const scoreB = parseFloat(b.confidence_score) || 0;
      return scoreB - scoreA;
    });
  }, [analysisResults]);

  const filteredResults = useMemo(() => {
    if (!filterText) return sortedResults;
    
    const searchTerm = filterText.toLowerCase();
    return sortedResults.filter(result => {
      return (
        result.finding?.toLowerCase().includes(searchTerm) ||
        result.category?.toLowerCase().includes(searchTerm) ||
        result.severity?.toLowerCase().includes(searchTerm) ||
        result.recommendation?.toLowerCase().includes(searchTerm)
      );
    });
  }, [sortedResults, filterText]);

  if (authLoading) {
    return (
      <div className="App">
        <div className="loading-container">
          <div className="loading-spinner"></div>
          <div className="loading-text">Загрузка...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="App">
      <div className="medical-decoration dna">🧬</div>
      <div className="medical-decoration molecule">⚛️</div>
      <div className="medical-decoration microscope">🔬</div>
      
      <header className="App-header">
        <div className="header-top">
          {user ? (
            <UserProfile user={user} onSignOut={handleSignOut} />
          ) : (
            <button 
              className="auth-btn"
              onClick={() => setAuthModalOpen(true)}
            >
              👤 Войти
            </button>
          )}
        </div>
        
        <h1>Анализатор Клинических Протоколов</h1>
        <p className="subtitle">Профессиональный анализ медицинских документов с использованием NLP и LLM</p>
        <div className="features">
          <div className="feature">
            <span>🤖</span>
            <span>ИИ Анализ</span>
          </div>
          <div className="feature">
            <span>📊</span>
            <span>Детальная Статистика</span>
          </div>
          <div className="feature">
            <span>📚</span>
            <span>PubMed Интеграция</span>
          </div>
        </div>
        
        {user && (
          <div className="header-actions">
            <button 
              className="history-btn"
              onClick={() => setShowHistory(!showHistory)}
            >
              📚 {showHistory ? 'Скрыть историю' : 'История анализов'}
            </button>
          </div>
        )}
      </header>
      
      <main>
        {user && showHistory && (
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

        {isLoading && (
          <LoadingIndicator 
            stage={currentStage} 
            progress={progress}
          />
        )}

        {errorMessage && (
          <ErrorMessage 
            message={errorMessage} 
            onClose={() => setErrorMessage('')} 
          />
        )}

        {analysisData && !isLoading && (
          <div className="results-section">
            <div className="glass-card">
              <h2>📋 Сводка документа</h2>
              {documentSummary && (
                <div className="document-summary">
                  <div className="summary-grid">
                    <div className="summary-item">
                      <strong>📄 Тип документа:</strong>
                      <span>{documentSummary.document_type || 'Не определен'}</span>
                    </div>
                    <div className="summary-item">
                      <strong>👤 Пациент:</strong>
                      <span>{documentSummary.patient_info || 'Информация недоступна'}</span>
                    </div>
                    <div className="summary-item">
                      <strong>📅 Дата:</strong>
                      <span>{documentSummary.date || 'Не указана'}</span>
                    </div>
                    <div className="summary-item">
                      <strong>🏥 Учреждение:</strong>
                      <span>{documentSummary.institution || 'Не указано'}</span>
                    </div>
                  </div>
                  
                  {documentSummary.key_findings && (
                    <div className="key-findings">
                      <h3>🔍 Ключевые находки:</h3>
                      <p>{documentSummary.key_findings}</p>
                    </div>
                  )}
                </div>
              )}
            </div>

            <div className="glass-card">
              <div className="results-header">
                <h2>📊 Результаты анализа ({filteredResults.length})</h2>
                <div className="filter-controls">
                  <input
                    type="text"
                    placeholder="🔍 Поиск по результатам..."
                    value={filterText}
                    onChange={(e) => setFilterText(e.target.value)}
                    className="filter-input"
                  />
                </div>
              </div>
              
              <ResultsTable results={filteredResults} />
              
              <ExportButtons 
                results={filteredResults}
                documentSummary={documentSummary}
                filename={analysisData.filename}
              />
            </div>
          </div>
        )}
      </main>
      
      <AuthModal 
        isOpen={authModalOpen}
        onClose={() => setAuthModalOpen(false)}
        onAuthSuccess={() => setAuthModalOpen(false)}
      />
    </div>
  );
}

export default App;