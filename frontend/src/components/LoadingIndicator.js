import React from 'react';

const LoadingIndicator = () => {
  return (
    <div className="loading-container fade-in-up">
      <div className="loading-spinner"></div>
      <div className="loading-text">Анализ документа в процессе</div>
      <div className="loading-subtext">
        🔬 Извлекаем препараты с помощью ИИ
        <br />
        🏥 Проверяем регуляторные базы данных
        <br />
        📚 Ищем исследования в PubMed
        <br />
        🧠 Генерируем GRADE анализ
      </div>
      <div className="loading-progress"></div>
    </div>
  );
};

export default LoadingIndicator;