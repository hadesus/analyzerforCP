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
      // More realistic progress simulation
      let currentProgress = 0;
      const progressInterval = setInterval(() => {
        currentProgress += Math.random() * 5 + 2; // 2-7% increments
        setProgress(Math.min(currentProgress, 85));
      }, 800);

      // Stage progression with realistic timing
      setTimeout(() => setCurrentStage('extraction'), 1000);
      setTimeout(() => setProgress(20), 1500);
      
      setTimeout(() => setCurrentStage('normalization'), 3000);
      setTimeout(() => setProgress(35), 3500);
      
      setTimeout(() => setCurrentStage('regulatory'), 5000);
      setTimeout(() => setProgress(50), 5500);
      
      setTimeout(() => setCurrentStage('pubmed'), 7000);
      setTimeout(() => setProgress(65), 7500);
      
      setTimeout(() => setCurrentStage('analysis'), 9000);
      setTimeout(() => setProgress(80), 9500);

      const response = await axios.post('http://localhost:8000/analyze', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 600000, // 10 minutes for complex documents
      });
      
      clearInterval(progressInterval);
      setProgress(100);
      
      // Small delay to show 100% completion
      await new Promise(resolve => setTimeout(resolve, 500));
      onUploadSuccess(response.data);
    } catch (error) {
      console.error('Full error object:', error);
      console.error('Error response:', error.response);
      console.error('Error request:', error.request);
      
      let message = 'Произошла непредвиденная ошибка.';
      if (error.response) {
        // The request was made and the server responded with a status code
        // that falls out of the range of 2xx
        console.error('Server responded with error:', error.response.status, error.response.data);
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
        console.error('No response received:', error.request);
        message = 'Не удалось получить ответ от сервера. Проверьте, запущен ли бэкенд.';
      } else if (error.code === 'ECONNABORTED') {
        console.error('Request timeout');
        message = 'Анализ занял слишком много времени (превышен лимит 5 минут). Попробуйте файл меньшего размера.';
      } else {
        // Something happened in setting up the request that triggered an Error
        console.error('Request setup error:', error.message);
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
