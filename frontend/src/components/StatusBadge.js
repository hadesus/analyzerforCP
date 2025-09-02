import React from 'react';

const StatusBadge = ({ status, isDosage = false }) => {
  if (!status) return <span className="status-badge status-not-found">Нет данных</span>;

  const getStatusClass = (status, isDosage) => {
    if (isDosage) {
      switch (status.toLowerCase()) {
        case 'within_range':
          return 'status-approved';
        case 'below_range':
        case 'above_range':
          return 'status-error';
        case 'mismatch':
          return 'status-not-found';
        default:
          return 'status-not-found';
      }
    }

    const statusLower = status.toLowerCase();
    if (statusLower.includes('approved') || statusLower.includes('found')) {
      return 'status-approved';
    }
    if (statusLower.includes('error')) {
      return 'status-error';
    }
    return 'status-not-found';
  };

  const getStatusText = (status, isDosage) => {
    if (isDosage) {
      switch (status.toLowerCase()) {
        case 'within_range':
          return 'В норме';
        case 'below_range':
          return 'Ниже нормы';
        case 'above_range':
          return 'Выше нормы';
        case 'mismatch':
          return 'Несовместимо';
        default:
          return status;
      }
    }
    return status;
  };

  return (
    <span className={`status-badge ${getStatusClass(status, isDosage)}`}>
      {getStatusText(status, isDosage)}
    </span>
  );
};

export default StatusBadge;