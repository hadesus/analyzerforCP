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
      const response = await axios.post('/analyze', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 300000, // 5 minutes
      });
      onUploadSuccess(response.data);
    } catch (error) {
      let message = 'Произошла непредвиденная ошибка.';
      if (error.response) {
        // The request was made and the server responded with a status code
        // that falls out of the range of 2xx
        const detail = error.response.data.detail;
        if (typeof detail === 'string') {
          message = `Ошибка от сервера: ${detail}`;
        } else if (typeof detail === 'object' && detail !== null) {
          message = `Ошибка от сервера: ${JSON.stringify(detail)}`;
        } else {
          message = `Ошибка от сервера: ${error.response.status} ${error.response.statusText}`;
        }
      } else if (error.request) {
        // The request was made but no response was received
        message = 'Не удалось получить ответ от сервера. Проверьте, запущен ли бэкенд.';
      } else if (error.code === 'ECONNABORTED') {
        message = 'Анализ занял слишком много времени (превышен лимит 5 минут). Попробуйте файл меньшего размера.';
      } else {
        // Something happened in setting up the request that triggered an Error
        message = `Ошибка при настройке запроса: ${error.message}`;
      }
      setErrorMessage(message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleDragEnter = (e) => { e.preventDefault(); e.stopPropagation(); setIsDragOver(true); };
  const handleDragLeave = (e) => { e.preventDefault(); e.stopPropagation(); setIsDragOver(false); };
  const handleDragOver = (e) => { e.preventDefault(); e.stopPropagation(); };

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
