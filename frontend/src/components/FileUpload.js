import React, { useState } from 'react';
import axios from 'axios';

const FileUpload = ({ onUploadSuccess, setIsLoading, setErrorMessage, setCurrentStage, setProgress }) => {
  const [isDragOver, setIsDragOver] = useState(false);

  const handleFileUpload = async (file) => {
    if (!file) return;

    setIsLoading(true);
    setErrorMessage('');
    onUploadSuccess(null);
    setCurrentStage('parsing');
    setProgress(0);

    const formData = new FormData();
    formData.append('file', file);

    try {
      // Simulate progress updates
      const progressInterval = setInterval(() => {
        setProgress(prev => Math.min(prev + Math.random() * 10, 90));
      }, 1000);

      setCurrentStage('extraction');
      await new Promise(resolve => setTimeout(resolve, 500));
      
      setCurrentStage('normalization');
      await new Promise(resolve => setTimeout(resolve, 300));
      
      setCurrentStage('regulatory');
      await new Promise(resolve => setTimeout(resolve, 300));
      
      setCurrentStage('pubmed');
      await new Promise(resolve => setTimeout(resolve, 300));
      
      setCurrentStage('analysis');

      const response = await axios.post('http://localhost:8000/analyze', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 300000, // 5 minutes
      });
      
      clearInterval(progressInterval);
      setProgress(100);
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
      setCurrentStage('parsing');
      setProgress(0);
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
      className={`file-upload-container ${isDragOver ? 'drag-over' : ''}`}
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
      <div className="upload-icon">📋</div>
      <p>Перетащите .docx файл сюда или нажмите для выбора</p>
      <p className="upload-hint">Поддерживаются только файлы формата .docx</p>
      <div className="upload-features">
        <div className="upload-feature">
          <span className="medical-icon">🔍</span>
          <span>NLP извлечение препаратов</span>
        </div>
        <div className="upload-feature">
          <span className="medical-icon">🏛️</span>
          <span>Проверка регуляторных статусов</span>
        </div>
        <div className="upload-feature">
          <span className="medical-icon">📈</span>
          <span>LLM анализ доказательности</span>
        </div>
      </div>
    </div>
  );
};

export default FileUpload;
