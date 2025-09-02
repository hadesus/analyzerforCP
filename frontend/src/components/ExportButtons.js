import React from 'react';
import axios from 'axios';

const ExportButtons = ({ results }) => {
  const handleExport = async (format) => {
    try {
      const response = await axios.post(`http://localhost:8000/export/${format}`, results, {
        responseType: 'blob', // Important for file downloads
      });

      // Create a URL for the blob
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `analysis_report.${format}`);

      // Append to html link element page
      document.body.appendChild(link);

      // Start download
      link.click();

      // Clean up and remove the link
      link.parentNode.removeChild(link);
      window.URL.revokeObjectURL(url);

    } catch (error) {
      console.error(`Error exporting to ${format}:`, error);
      alert(`Не удалось экспортировать файл в формате ${format}.`);
    }
  };

  return (
    <div className="export-container">
      <button onClick={() => handleExport('docx')} className="export-btn docx">
        <span>📄</span>
        Экспорт в DOCX
      </button>
      <button onClick={() => handleExport('xlsx')} className="export-btn xlsx">
        <span>📊</span>
        Экспорт в Excel (XLSX)
      </button>
      <button onClick={() => handleExport('json')} className="export-btn json">
        <span>🔧</span>
        Экспорт в JSON
      </button>
    </div>
  );
};

export default ExportButtons;
