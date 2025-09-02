import React from 'react';

const LoadingIndicator = ({ currentStage = 'parsing', progress = 0 }) => {
  const stages = [
    { key: 'parsing', label: 'Парсинг документа', icon: '📄', description: 'Извлекаем текст из .docx файла' },
    { key: 'extraction', label: 'Извлечение препаратов', icon: '🔬', description: 'NLP анализ для поиска лекарственных средств' },
    { key: 'normalization', label: 'Нормализация названий', icon: '🏷️', description: 'Определяем МНН препаратов' },
    { key: 'regulatory', label: 'Регуляторные проверки', icon: '🏛️', description: 'Проверяем статусы в FDA, EMA, BNF, WHO' },
    { key: 'pubmed', label: 'Поиск исследований', icon: '📚', description: 'Ищем исследования в PubMed' },
    { key: 'analysis', label: 'LLM анализ', icon: '📊', description: 'Генерируем GRADE оценку и заключение' }
  ];

  const currentStageIndex = stages.findIndex(stage => stage.key === currentStage);
  const currentStageData = stages[currentStageIndex] || stages[0];
  
  // Calculate more accurate progress
  const baseProgress = (currentStageIndex / stages.length) * 100;
  const displayProgress = Math.max(progress, baseProgress);

  return (
    <div className="loading-container fade-in-up">
      <div className="loading-spinner"></div>
      <div className="loading-text">Анализ документа в процессе</div>
      <div className="loading-stage">
        <div className="stage-icon">{currentStageData.icon}</div>
        <div className="stage-info">
          <div className="stage-title">{currentStageData.label}</div>
          <div className="stage-description">{currentStageData.description}</div>
        </div>
      </div>
      
      <div className="progress-container">
        <div className="progress-bar">
          <div 
            className="progress-fill" 
            style={{ width: `${displayProgress}%` }}
          ></div>
        </div>
        <div className="progress-text">{Math.round(displayProgress)}%</div>
      </div>

      <div className="stages-list">
        {stages.map((stage, index) => (
          <div 
            key={stage.key} 
            className={`stage-item ${index <= currentStageIndex ? 'completed' : ''} ${index === currentStageIndex ? 'active' : ''}`}
          >
            <div className="stage-marker">
              {index < currentStageIndex ? '✅' : index === currentStageIndex ? stage.icon : '⏳'}
            </div>
            <span className="stage-label">{stage.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
};

export default LoadingIndicator;