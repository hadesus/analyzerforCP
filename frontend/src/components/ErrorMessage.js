import React from 'react';

const ErrorMessage = ({ message }) => {
  return (
    <div className="error-container fade-in-up">
      <div className="error-icon">⚠️</div>
      <div className="error-message">{message}</div>
    </div>
  );
};

export default ErrorMessage;