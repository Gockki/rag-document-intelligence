// frontend/src/components/DocumentManager.js
import React, { useState } from 'react';

const DocumentManager = ({ documents, userEmail, onDocumentDeleted, onRefresh }) => {
  const [deleteModal, setDeleteModal] = useState(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const API_BASE = 'http://localhost:8000';

  const deleteDocument = async (doc) => {
    setIsDeleting(true);
    try {
      const response = await fetch(
        `${API_BASE}/documents/${doc.id}?user_email=${userEmail}`, 
        { method: 'DELETE' }
      );

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to delete document');
      }

      const result = await response.json();
      
      // Notify parent component
      if (onDocumentDeleted) {
        onDocumentDeleted(doc.id, result.filename);
      }
      
      // Refresh documents list
      if (onRefresh) {
        onRefresh();
      }
      
      setDeleteModal(null);
    } catch (error) {
      alert(`Failed to delete document: ${error.message}`);
    } finally {
      setIsDeleting(false);
    }
  };

  const formatFileSize = (bytes) => {
    if (bytes < 1024) return bytes + ' B';
    else if (bytes < 1048576) return Math.round(bytes / 1024) + ' KB';
    else return Math.round(bytes / 1048576) + ' MB';
  };

  return (
    <div className="card">
      <div className="card-header" style={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center' 
      }}>
        <span>✅ Documents ({documents.length})</span>
        <button
          onClick={onRefresh}
          style={{
            background: 'none',
            border: '1px solid #e5e7eb',
            borderRadius: '4px',
            padding: '2px 6px',
            fontSize: '12px',
            cursor: 'pointer'
          }}
        >
          🔄 Refresh
        </button>
      </div>
      
      <div style={{ maxHeight: '400px', overflowY: 'auto' }}>
        {documents.map((file) => (
          <div key={file.id} className="file-item" style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            padding: '0.75rem',
            borderBottom: '1px solid #f3f4f6',
            transition: 'background-color 0.2s'
          }}
          onMouseOver={(e) => e.currentTarget.style.backgroundColor = '#f9fafb'}
          onMouseOut={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
          >
            <div>
              <div className="file-name" style={{ fontWeight: '500' }}>
                {file.original_filename || file.filename}
              </div>
              <div className="file-meta" style={{ 
                fontSize: '0.75rem', 
                color: '#6b7280',
                marginTop: '0.25rem' 
              }}>
                {formatFileSize(file.file_size)} • {file.chunk_count} chunks
                {file.has_embeddings && ' • 🔍 Indexed'}
                <br />
                Uploaded: {new Date(file.upload_time).toLocaleDateString()}
              </div>
            </div>
            <button
              onClick={() => setDeleteModal(file)}
              style={{
                background: 'none',
                border: 'none',
                color: '#dc2626',
                cursor: 'pointer',
                padding: '4px',
                fontSize: '18px',
                opacity: 0.6,
                transition: 'opacity 0.2s'
              }}
              onMouseOver={(e) => e.target.style.opacity = 1}
              onMouseOut={(e) => e.target.style.opacity = 0.6}
              title="Delete document"
            >
              🗑️
            </button>
          </div>
        ))}
      </div>

      {/* Delete Confirmation Modal */}
      {deleteModal && (
        <div style={{
          position: 'fixed',
          inset: 0,
          backgroundColor: 'rgba(0, 0, 0, 0.5)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 100
        }}>
          <div style={{
            background: 'white',
            borderRadius: '0.5rem',
            padding: '1.5rem',
            maxWidth: '400px',
            width: '90%',
            boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1)'
          }}>
            <h3 style={{ marginBottom: '1rem' }}>Confirm Delete</h3>
            <p style={{ marginBottom: '1.5rem', color: '#4b5563' }}>
              Are you sure you want to delete "<strong>{deleteModal.original_filename || deleteModal.filename}</strong>"? 
              This will remove the document and all its embeddings permanently.
            </p>
            
            <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end' }}>
              <button
                onClick={() => setDeleteModal(null)}
                disabled={isDeleting}
                style={{
                  padding: '0.5rem 1rem',
                  background: '#e5e7eb',
                  border: 'none',
                  borderRadius: '0.25rem',
                  cursor: 'pointer'
                }}
              >
                Cancel
              </button>
              <button
                onClick={() => deleteDocument(deleteModal)}
                disabled={isDeleting}
                style={{
                  padding: '0.5rem 1rem',
                  background: '#dc2626',
                  color: 'white',
                  border: 'none',
                  borderRadius: '0.25rem',
                  cursor: 'pointer',
                  opacity: isDeleting ? 0.5 : 1
                }}
              >
                {isDeleting ? 'Deleting...' : 'Delete'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default DocumentManager;