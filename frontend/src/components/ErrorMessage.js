import React from 'react';

const ErrorMessage = ({ message }) => {
  return (
    <div className="error-container fade-in-up">
      <div className="error-icon">⚠️</div>
      <div className="error-message">
        <strong>Произошла ошибка при анализе:</strong>
        <br />
        {message}
        <br />
        <small style={{ opacity: 0.8, marginTop: '1rem', display: 'block' }}>
          Попробуйте загрузить другой файл или проверьте подключение к интернету
        </small>
      </div>
    </div>
  );
};

export default ErrorMessage;