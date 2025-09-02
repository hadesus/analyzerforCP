import React from 'react';

const GradeBadge = ({ grade }) => {
  if (!grade) return <span className="grade-badge grade-very-low">Не определен</span>;

  const getGradeClass = (grade) => {
    const gradeLower = grade.toLowerCase();
    if (gradeLower.includes('high')) return 'grade-high';
    if (gradeLower.includes('moderate')) return 'grade-moderate';
    if (gradeLower.includes('low') && !gradeLower.includes('very')) return 'grade-low';
    if (gradeLower.includes('very low')) return 'grade-very-low';
    return 'grade-very-low';
  };

  const getGradeIcon = (grade) => {
    const gradeLower = grade.toLowerCase();
    if (gradeLower.includes('high')) return '🟢';
    if (gradeLower.includes('moderate')) return '🟡';
    if (gradeLower.includes('low') && !gradeLower.includes('very')) return '🟠';
    if (gradeLower.includes('very low')) return '🔴';
    return '❓';
  };

  return (
    <div className={`grade-badge ${getGradeClass(grade)}`}>
      <span style={{ marginRight: '0.5rem' }}>{getGradeIcon(grade)}</span>
      {grade}
    </div>
  );
};

export default GradeBadge;