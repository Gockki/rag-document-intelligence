// frontend/src/App.js
import React, { useState, useRef, useEffect } from 'react';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import Auth from './components/Auth';
import DocumentManager from './components/DocumentManager';

// Loading component
const LoadingSpinner = () => (
  <div style={{
    minHeight: '100vh',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    background: 'linear-gradient(135deg, #f0f9ff 0%, #ffffff 50%, #faf5ff 100%)'
  }}>
    <div style={{ textAlign: 'center' }}>
      <div style={{
        width: '40px',
        height: '40px',
        border: '4px solid #e5e7eb',
        borderTop: '4px solid #3b82f6',
        borderRadius: '50%',
        animation: 'spin 1s linear infinite',
        margin: '0 auto 1rem'
      }}></div>
      <p style={{ color: '#6b7280' }}>Loading RAG Platform...</p>
    </div>
  </div>
);

// Your existing DocumentIntelligence component with auth integration
const DocumentIntelligence = () => {
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [uploadedFiles, setUploadedFiles] = useState([]);
  const [isUploading, setIsUploading] = useState(false);
  const [chatSessions, setChatSessions] = useState([]);
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [currentSessionName, setCurrentSessionName] = useState('New Chat');
  const [showHistory, setShowHistory] = useState(true);
  const [showUserMenu, setShowUserMenu] = useState(false);
  const fileInputRef = useRef(null);
  const messagesEndRef = useRef(null);

  // Get user data from auth context
  const { user, signOut } = useAuth();
  const API_BASE = 'http://localhost:8000';

  // Use user's email from Supabase auth
  const userEmail = user?.email || 'demo@example.com';
  const userName = user?.user_metadata?.name || user?.email?.split('@')[0] || 'User';

  // Scroll to bottom of messages
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Load chat sessions on component mount
  useEffect(() => {
    loadChatSessions();
    loadDocuments();
  }, []);

  // Load chat sessions from API
  const loadChatSessions = async () => {
    try {
      const response = await fetch(`${API_BASE}/chat/sessions?user_email=${userEmail}`);
      if (response.ok) {
        const data = await response.json();
        setChatSessions(data.sessions || []);
      }
    } catch (error) {
      console.error('Failed to load chat sessions:', error);
    }
  };

  // Load user documents
  const loadDocuments = async () => {
    try {
      const response = await fetch(`${API_BASE}/documents?user_email=${userEmail}`);
      if (response.ok) {
        const data = await response.json();
        setUploadedFiles(data.documents || []);
      }
    } catch (error) {
      console.error('Failed to load documents:', error);
    }
  };

  // Handle user logout
  const handleLogout = async () => {
    try {
      await signOut();
    } catch (error) {
      console.error('Logout error:', error);
    }
  };

  // Start new chat session
  const startNewChat = () => {
    setCurrentSessionId(null);
    setCurrentSessionName('New Chat');
    setMessages([]);
  };

  // Load specific chat session
  const loadChatSession = async (sessionId, sessionName) => {
    try {
      setCurrentSessionId(sessionId);
      setCurrentSessionName(sessionName);
      
      // Load chat history for this session
      const response = await fetch(`${API_BASE}/chat/history?user_email=${userEmail}&limit=100`);
      if (response.ok) {
        const data = await response.json();
        
        // Filter messages for this session and convert to frontend format
        const sessionMessages = data.messages
          .filter(msg => msg.session_id === sessionId)
          .map(msg => ({
            type: msg.message_type,
            content: msg.content,
            timestamp: new Date(msg.created_at).toLocaleString(),
            confidence: msg.confidence_score,
            sources: [] // Would need to be populated from source_documents
          }))
          .reverse(); // Reverse to get chronological order
        
        setMessages(sessionMessages);
      }
    } catch (error) {
      console.error('Failed to load chat session:', error);
      addSystemMessage(`❌ Failed to load chat session: ${error.message}`);
    }
  };

  // Add system message
  const addSystemMessage = (content) => {
    setMessages(prev => [...prev, {
      type: 'system',
      content,
      timestamp: new Date().toLocaleString()
    }]);
  };

  // Upload file function
  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    setIsUploading(true);
    const formData = new FormData();
    formData.append('file', file);
    formData.append('user_email', userEmail);

    try {
      const response = await fetch(`${API_BASE}/upload`, {
        method: 'POST',
        body: formData,
      });

      if (response.ok) {
        const result = await response.json();
        
        // Refresh documents list
        loadDocuments();
        
        // Add success message to chat
        addSystemMessage(`✅ Document "${file.name}" uploaded successfully! Created ${result.chunks_created} chunks.`);
      } else {
        const error = await response.json();
        throw new Error(error.detail || 'Upload failed');
      }
    } catch (error) {
      addSystemMessage(`❌ Upload failed: ${error.message}`);
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  // Send query function
  const handleSendMessage = async () => {
    if (!inputValue.trim() || isLoading) return;

    const userMessage = {
      type: 'user',
      content: inputValue,
      timestamp: new Date().toLocaleString()
    };

    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);
    const question = inputValue;
    setInputValue('');

    try {
      const response = await fetch(`${API_BASE}/query`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          question: question,
          max_results: 3,
          user_email: userEmail,
          session_id: currentSessionId
        }),
      });

      if (response.ok) {
        const result = await response.json();
        
        // Update current session info
        if (!currentSessionId) {
          setCurrentSessionId(result.session_id);
          if (currentSessionName === 'New Chat') {
            setCurrentSessionName(`Chat ${new Date().toLocaleTimeString()}`);
          }
          // Reload sessions to include the new one
          loadChatSessions();
        }
        
        setMessages(prev => [...prev, {
          type: 'assistant',
          content: result.answer,
          sources: result.sources,
          confidence: result.confidence,
          timestamp: new Date().toLocaleString()
        }]);
      } else {
        const error = await response.json();
        throw new Error(error.detail || 'Query failed');
      }
    } catch (error) {
      addSystemMessage(`❌ Query failed: ${error.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50">
      {/* Header with User Menu */}
      <header className="header">
        <div className="header-container">
          <div className="header-left">
            <div className="logo">🧠</div>
            <div>
              <h1 className="header-title">Document Intelligence Platform</h1>
              <p className="header-subtitle">RAG-powered with Authentication</p>
            </div>
          </div>
          <div style={{ position: 'relative' }}>
            <button
              onClick={() => setShowUserMenu(!showUserMenu)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                background: 'white',
                border: '1px solid #e5e7eb',
                borderRadius: '0.5rem',
                padding: '0.5rem 1rem',
                cursor: 'pointer',
                fontSize: '0.875rem'
              }}
            >
              <div style={{
                width: '32px',
                height: '32px',
                borderRadius: '50%',
                background: 'linear-gradient(135deg, #3b82f6, #8b5cf6)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'white',
                fontWeight: 'bold'
              }}>
                {userName.charAt(0).toUpperCase()}
              </div>
              <div>
                <div style={{ fontWeight: '500' }}>{userName}</div>
                <div style={{ fontSize: '0.75rem', color: '#6b7280' }}>{userEmail}</div>
              </div>
              <span style={{ fontSize: '0.75rem' }}>▼</span>
            </button>

            {/* User Dropdown Menu */}
            {showUserMenu && (
              <div style={{
                position: 'absolute',
                top: '100%',
                right: 0,
                background: 'white',
                border: '1px solid #e5e7eb',
                borderRadius: '0.5rem',
                boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1)',
                marginTop: '0.5rem',
                minWidth: '200px',
                zIndex: 50
              }}>
                <div style={{ padding: '0.5rem' }}>
                  <div style={{
                    padding: '0.5rem',
                    borderBottom: '1px solid #f3f4f6',
                    marginBottom: '0.5rem'
                  }}>
                    <div style={{ fontWeight: '500', fontSize: '0.875rem' }}>{userName}</div>
                    <div style={{ fontSize: '0.75rem', color: '#6b7280' }}>{userEmail}</div>
                  </div>
                  
                  <button
                    onClick={() => {
                      setShowUserMenu(false);
                      handleLogout();
                    }}
                    style={{
                      width: '100%',
                      padding: '0.5rem',
                      textAlign: 'left',
                      background: 'none',
                      border: 'none',
                      borderRadius: '0.25rem',
                      cursor: 'pointer',
                      fontSize: '0.875rem',
                      color: '#dc2626'
                    }}
                    onMouseOver={(e) => e.target.style.backgroundColor = '#fef2f2'}
                    onMouseOut={(e) => e.target.style.backgroundColor = 'transparent'}
                  >
                    🚪 Sign Out
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </header>

      <div className="main-container">
        
        {/* Chat History Sidebar */}
        <div className={`sidebar ${showHistory ? '' : 'hidden'}`}>
          <div className="card">
            <div className="card-header">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span>💬 Chat History</span>
                <button 
                  onClick={startNewChat}
                  style={{
                    background: '#3b82f6',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    padding: '4px 8px',
                    fontSize: '12px',
                    cursor: 'pointer'
                  }}
                >
                  + New
                </button>
              </div>
            </div>
            
            <div style={{ maxHeight: '300px', overflowY: 'auto' }}>
              {chatSessions.length === 0 ? (
                <div style={{ padding: '1rem', textAlign: 'center', color: '#6b7280', fontSize: '0.875rem' }}>
                  No chat history yet. Start a conversation!
                </div>
              ) : (
                chatSessions.map((session) => (
                  <div
                    key={session.id}
                    onClick={() => loadChatSession(session.id, session.session_name)}
                    style={{
                      padding: '0.75rem',
                      margin: '0.5rem 0',
                      backgroundColor: currentSessionId === session.id ? '#dbeafe' : '#f9fafb',
                      border: currentSessionId === session.id ? '1px solid #3b82f6' : '1px solid #e5e7eb',
                      borderRadius: '0.5rem',
                      cursor: 'pointer',
                      fontSize: '0.875rem'
                    }}
                  >
                    <div style={{ fontWeight: '500', marginBottom: '0.25rem' }}>
                      {session.session_name}
                    </div>
                    <div style={{ color: '#6b7280', fontSize: '0.75rem' }}>
                      {session.message_count} messages • {new Date(session.last_message_at).toLocaleDateString()}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Upload Section */}
          <div className="card">
            <h3 className="card-header">📁 Upload Documents</h3>
            
            <div className="upload-area">
              <input
                type="file"
                ref={fileInputRef}
                onChange={handleFileUpload}
                accept=".txt,.pdf,.md"
                className="hidden"
              />
              <button
                onClick={() => fileInputRef.current?.click()}
                disabled={isUploading}
                className="upload-button"
              >
                {isUploading ? (
                  <div className="spinner"></div>
                ) : (
                  <span style={{fontSize: '2rem'}}>📄</span>
                )}
                <span className="upload-text">
                  {isUploading ? 'Uploading...' : 'Click to upload'}
                </span>
                <span className="upload-subtext">TXT, PDF, MD files</span>
              </button>
            </div>
          </div>

          {/* Uploaded Files */}
          {uploadedFiles.length > 0 && (
            <DocumentManager 
              documents={uploadedFiles}
              userEmail={userEmail}
              onDocumentDeleted={(docId, filename) => {
                // Näytä viesti chatissa
                addSystemMessage(`🗑️ Document "${filename}" has been deleted successfully.`);
      
                // Jos poistettu dokumentti oli ainoa, tyhjennä lista
                if (uploadedFiles.length === 1) {
                  setUploadedFiles([]);
                }
              }}
              onRefresh={loadDocuments}
          />
        )}
      </div>
      
        {/* Main Chat Area */}
        <div className="chat-container">
          
          {/* Chat Header */}
          <div className="chat-header">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div className="chat-title">
                💬 {currentSessionName}
                {currentSessionId && (
                  <span style={{ fontSize: '0.75rem', color: '#6b7280', marginLeft: '0.5rem' }}>
                    (Session #{currentSessionId})
                  </span>
                )}
              </div>
              <button
                onClick={() => setShowHistory(!showHistory)}
                style={{
                  background: 'none',
                  border: '1px solid #e5e7eb',
                  borderRadius: '4px',
                  padding: '4px 8px',
                  fontSize: '12px',
                  cursor: 'pointer'
                }}
              >
                {showHistory ? 'Hide' : 'Show'} History
              </button>
            </div>
          </div>

          {/* Messages */}
          <div className="messages-area">
            {messages.length === 0 ? (
              <div className="empty-state">
                <span style={{fontSize: '3rem'}}>🔍</span>
                <h3>Welcome, {userName}!</h3>
                <p>
                  {currentSessionId 
                    ? 'Continue your conversation or explore new topics in this session.'
                    : 'Upload documents and ask questions to see the RAG system in action. Try: "What is the main topic?" or "Summarize the key points"'
                  }
                </p>
              </div>
            ) : (
              messages.map((message, index) => (
                <div key={index} className={`message ${message.type}`}>
                  <div className="message-content">
                    
                    {message.type === 'assistant' && (
                      <div className="ai-header">
                        🧠 AI Response 
                        {message.confidence && (
                          <span> • Confidence: {(message.confidence * 100).toFixed(1)}%</span>
                        )}
                      </div>
                    )}
                    
                    <div className="message-text">{message.content}</div>
                    
                    {message.sources && message.sources.length > 0 && (
                      <div className="sources-section">
                        <div className="sources-title">Sources:</div>
                        <div>
                          {message.sources.map((source, idx) => (
                            <div key={idx} className="source-item">
                              <div className="source-name">{source.source}</div>
                              <div className="source-similarity">
                                Similarity: {(source.similarity * 100).toFixed(1)}%
                              </div>
                              <div className="source-preview">
                                "{source.content_preview}"
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                    
                    <div className="message-timestamp">
                      {message.timestamp}
                    </div>
                  </div>
                </div>
              ))
            )}
            
            {isLoading && (
              <div className="message assistant">
                <div className="loading-message">
                  <div className="spinner"></div>
                  <span>AI is thinking...</span>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input Area */}
          <div className="input-area">
            <div className="input-container">
              <div className="input-wrapper">
                <textarea
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder={
                    currentSessionId 
                      ? "Continue your conversation..." 
                      : "Ask a question about your documents..."
                  }
                  className="message-input"
                  rows={2}
                  disabled={isLoading}
                />
              </div>
              <button
                onClick={handleSendMessage}
                disabled={!inputValue.trim() || isLoading}
                className="send-button"
              >
                💬
              </button>
            </div>
            
            <div className="input-help">
              Press Enter to send, Shift+Enter for new line
              {currentSessionId && (
                <span> • Session #{currentSessionId}</span>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Click outside to close user menu */}
      {showUserMenu && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            zIndex: 40
          }}
          onClick={() => setShowUserMenu(false)}
        />
      )}
    </div>
  );
};

// Main app component with auth logic
const AppContent = () => {
  const { user, loading } = useAuth();

  // Show loading spinner while checking auth
  if (loading) {
    return <LoadingSpinner />;
  }

  // Show login if no user
  if (!user) {
    return <Auth />;
  }

  // Show main app if user is logged in
  return <DocumentIntelligence />;
};

// Root app with providers
function App() {
  return (
    <AuthProvider>
      <AppContent />
      <style jsx global>{`
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      `}</style>
    </AuthProvider>
  );
}

export default App;