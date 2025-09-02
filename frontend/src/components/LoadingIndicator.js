import React from 'react';

const LoadingIndicator = () => {
  return (
    <div className="loading-container fade-in-up">
      <div className="loading-spinner"></div>
      <div className="loading-text">Анализ документа в процессе</div>
      <div className="loading-subtext">
        Извлекаем препараты, проверяем регуляторные базы и анализируем данные...
        <br />
        Это может занять несколько минут.
      </div>
    </div>
  );
};

export default LoadingIndicator;