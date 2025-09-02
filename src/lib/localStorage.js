// Local storage utilities for protocol analysis results

const STORAGE_KEY = 'clinical_protocols';

export const localStorage = {
  // Save a protocol analysis to local storage
  saveProtocol(filename, documentSummary, analysisResults) {
    try {
      const protocols = this.getAllProtocols();
      const newProtocol = {
        id: Date.now().toString(),
        filename,
        document_summary: documentSummary,
        analysis_results: analysisResults,
        upload_date: new Date().toISOString(),
        created_at: new Date().toISOString()
      };
      
      protocols.unshift(newProtocol); // Add to beginning
      
      // Keep only last 50 protocols to avoid storage bloat
      if (protocols.length > 50) {
        protocols.splice(50);
      }
      
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(protocols));
      return newProtocol;
    } catch (error) {
      console.error('Error saving protocol to localStorage:', error);
      throw new Error('Не удалось сохранить протокол');
    }
  },

  // Get all saved protocols
  getAllProtocols() {
    try {
      const stored = window.localStorage.getItem(STORAGE_KEY);
      return stored ? JSON.parse(stored) : [];
    } catch (error) {
      console.error('Error reading protocols from localStorage:', error);
      return [];
    }
  },

  // Get specific protocol by ID
  getProtocol(protocolId) {
    const protocols = this.getAllProtocols();
    return protocols.find(p => p.id === protocolId);
  },

  // Delete a protocol
  deleteProtocol(protocolId) {
    try {
      const protocols = this.getAllProtocols();
      const filtered = protocols.filter(p => p.id !== protocolId);
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(filtered));
      return true;
    } catch (error) {
      console.error('Error deleting protocol:', error);
      throw new Error('Не удалось удалить протокол');
    }
  },

  // Search protocols by drug name or content
  searchProtocols(searchTerm) {
    const protocols = this.getAllProtocols();
    const term = searchTerm.toLowerCase();
    
    return protocols.filter(protocol => {
      // Search in filename
      if (protocol.filename.toLowerCase().includes(term)) return true;
      
      // Search in document summary
      if (protocol.document_summary && protocol.document_summary.toLowerCase().includes(term)) return true;
      
      // Search in drug names
      if (protocol.analysis_results) {
        return protocol.analysis_results.some(result => {
          const drugName = result.source_data?.drug_name_source?.toLowerCase() || '';
          const innName = result.normalization?.inn_name?.toLowerCase() || '';
          return drugName.includes(term) || innName.includes(term);
        });
      }
      
      return false;
    });
  },

  // Get storage statistics
  getStorageStats() {
    const protocols = this.getAllProtocols();
    const totalDrugs = protocols.reduce((sum, protocol) => {
      return sum + (protocol.analysis_results?.length || 0);
    }, 0);
    
    return {
      totalProtocols: protocols.length,
      totalDrugs,
      storageSize: new Blob([window.localStorage.getItem(STORAGE_KEY) || '']).size
    };
  },

  // Clear all stored protocols
  clearAll() {
    try {
      window.localStorage.removeItem(STORAGE_KEY);
      return true;
    } catch (error) {
      console.error('Error clearing protocols:', error);
      throw new Error('Не удалось очистить хранилище');
    }
  }
};