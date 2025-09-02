import React from 'react';
import axios from 'axios';

const ExportButtons = ({ results }) => {
  const handleExport = async (format) => {
    try {
      const response = await axios.post(`/export/${format}`, results, {
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
    <div className="export-buttons" style={{ marginTop: '20px', textAlign: 'right' }}>
      <button onClick={() => handleExport('docx')} style={{ marginRight: '10px' }}>
        Экспорт в DOCX
      </button>
      <button onClick={() => handleExport('xlsx')} style={{ marginRight: '10px' }}>
        Экспорт в Excel (XLSX)
      </button>
      <button onClick={() => handleExport('json')}>
        Экспорт в JSON
      </button>
    </div>
  );
};

export default ExportButtons;
