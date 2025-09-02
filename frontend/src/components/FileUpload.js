import React, { useState } from 'react';
import axios from 'axios';

const FileUpload = ({ onUploadSuccess, setIsLoading, setErrorMessage }) => {
  const [isDragOver, setIsDragOver] = useState(false);

  const handleFileUpload = async (file) => {
    if (!file) return;

    setIsLoading(true);
    setErrorMessage('');
    onUploadSuccess(null);

    const formData = new FormData();
    formData.append('file', file);

    try {
      // Use a longer timeout for potentially long analysis times
      const response = await axios.post('/analyze', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        timeout: 300000, // 5 minutes timeout
      });
      onUploadSuccess(response.data.analysis_results);
    } catch (error) {
      const detail = error.response?.data?.detail;
      let message = 'Произошла ошибка при загрузке или анализе файла.';
      if (typeof detail === 'string') {
        message = detail;
      } else if (typeof detail?.detail === 'string') {
        message = detail.detail;
      } else if (error.code === 'ECONNABORTED') {
        message = 'Анализ занял слишком много времени (превышен лимит 5 минут). Попробуйте файл меньшего размера.';
      }
      setErrorMessage(message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleDragEnter = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
    const [file] = e.dataTransfer.files;
    if (file && file.name.endsWith('.docx')) {
      handleFileUpload(file);
    } else {
      setErrorMessage('Пожалуйста, выберите файл в формате .docx');
    }
  };

  const handleFileChange = (e) => {
    const [file] = e.target.files;
    handleFileUpload(file);
  };

  return (
    <div
      className={`file-upload-area ${isDragOver ? 'drag-over' : ''}`}
      onDrop={handleDrop}
      onDragOver={handleDragOver}
      onDragEnter={handleDragEnter}
      onDragLeave={handleDragLeave}
      onClick={() => document.getElementById('fileInput').click()}
    >
      <input
        type="file"
        id="fileInput"
        style={{ display: 'none' }}
        onChange={handleFileChange}
        accept=".docx"
      />
      <p>Перетащите .docx файл сюда или нажмите для выбора</p>
    </div>
  );
};

export default FileUpload;
