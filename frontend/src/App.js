// frontend/src/App.js
import React, { useState, useRef, useEffect } from 'react';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import Auth from './components/Auth';
import DocumentManager from './components/DocumentManager';
import { ThemeProvider } from './contexts/ThemeContext';
import DarkModeToggle from './components/DarkModeToggle';
import { 
  Brain, 
  Send,  
  MessageSquare, 
  LogOut, 
  FolderOpen,
  Plus,
  ChevronDown,
  Info,
  Search,
  Menu,
  X,
  Upload
} from 'lucide-react';

// Professional color scheme
const colors = {
  primary: '#1a1a2e',
  primaryDark: '#16213e',
  accent: '#0f4c81',
  bgPrimary: '#ffffff',
  bgSecondary: '#f8f9fa',
  bgTertiary: '#e9ecef',
  textPrimary: '#212529',
  textSecondary: '#495057',
  textMuted: '#6c757d',
  borderLight: '#dee2e6',
  borderMedium: '#ced4da',
  success: '#28a745',
  danger: '#dc3545',
  warning: '#ffc107'
};

// Loading component
const LoadingSpinner = () => (
  <div style={{
    minHeight: '100vh',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    background: colors.bgSecondary
  }}>
    <div style={{ textAlign: 'center' }}>
      <div style={{
        width: '40px',
        height: '40px',
        border: `3px solid ${colors.borderLight}`,
        borderTop: `3px solid ${colors.accent}`,
        borderRadius: '50%',
        animation: 'spin 1s linear infinite',
        margin: '0 auto 1rem'
      }}></div>
      <p style={{ color: colors.textMuted, fontSize: '14px' }}>Loading RAG Platform...</p>
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

  // Use user's email from Supabase auth - with proper fallback
  const userEmail = user?.email || 'demo@example.com';
  const userName = user?.user_metadata?.name || 
                  user?.user_metadata?.full_name ||
                  user?.email?.split('@')[0] || 
                  'User';

  // Scroll to bottom of messages
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Load chat sessions on component mount
  useEffect(() => {
    // Only load if we have a user with email
    if (user && user.email) {
      loadChatSessions();
      loadDocuments();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user]); // Re-run when user changes

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
      addSystemMessage(`Failed to load chat session: ${error.message}`);
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

    // Make sure we have a real user email
    const uploadEmail = user?.email || userEmail;
    
    console.log('DEBUG: uploadEmail =', uploadEmail);
    console.log('DEBUG: user?.email =', user?.email);
    console.log('DEBUG: userEmail fallback =', userEmail);

    setIsUploading(true);
    const formData = new FormData();
    formData.append('file', file);
    // user_email lähetetään query parametrina, ei FormDatassa
    
    // Debug FormData contents
    for (let [key, value] of formData.entries()) {
      console.log('FormData:', key, '=', value);
    }

    try {
      // Send email as query parameter instead of FormData
      const response = await fetch(`${API_BASE}/upload?user_email=${encodeURIComponent(uploadEmail)}`, {
        method: 'POST',
        body: formData,
      });

      console.log('Upload URL:', `${API_BASE}/upload?user_email=${encodeURIComponent(uploadEmail)}`);

      if (response.ok) {
        const result = await response.json();
        
        // Refresh documents list
        loadDocuments();
        
        // Add success message to chat
        const chunks = result?.chunks_created || result?.chunk_count || 'several';
        addSystemMessage(`Document "${file.name}" uploaded successfully! Created ${chunks} chunks.`);
      } else {
        const error = await response.json();
        throw new Error(error.detail || 'Upload failed');
      }
    } catch (error) {
      addSystemMessage(`Upload failed: ${error.message}`);
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
      addSystemMessage(`Query failed: ${error.message}`);
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
    <div style={{ minHeight: '100vh', background: colors.bgSecondary }}>
      {/* Professional Header */}
      <header style={{
        background: colors.primary,
        color: 'white',
        boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
      }}>
        <div style={{
          maxWidth: '1400px',
          margin: '0 auto',
          padding: '0.75rem 1.5rem',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <div style={{
              background: colors.accent,
              width: '40px',
              height: '40px',
              borderRadius: '4px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}>
              <Brain size={24} color="white" />
            </div>
            <div>
              <h1 style={{
                fontSize: '20px',
                fontWeight: '600',
                margin: 0,
                letterSpacing: '-0.5px'
              }}>
                Document Intelligence Platform
              </h1>
              <p style={{
                fontSize: '13px',
                margin: 0,
                opacity: 0.8
              }}>
                RAG-powered with Authentication
              </p>
            </div>
          </div>
          <div style={{ position: 'relative' }}>
            <button
              onClick={() => setShowUserMenu(!showUserMenu)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.75rem',
                background: 'rgba(255,255,255,0.1)',
                border: '1px solid rgba(255,255,255,0.2)',
                borderRadius: '4px',
                padding: '0.5rem 1rem',
                cursor: 'pointer',
                color: 'white',
                fontSize: '14px',
                transition: 'all 0.2s'
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = 'rgba(255,255,255,0.15)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = 'rgba(255,255,255,0.1)';
              }}
            >
              <div style={{
                width: '32px',
                height: '32px',
                borderRadius: '50%',
                background: colors.accent,
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
                <div style={{ fontSize: '0.75rem', opacity: 0.8 }}>{userEmail}</div>
              </div>
              <ChevronDown size={16} />
            </button>

            {/* User Dropdown Menu */}
            {showUserMenu && (
              <div style={{
                position: 'absolute',
                top: '100%',
                right: 0,
                background: 'white',
                border: `1px solid ${colors.borderLight}`,
                borderRadius: '4px',
                boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1)',
                marginTop: '0.5rem',
                minWidth: '200px',
                zIndex: 50
              }}>
                <div style={{ padding: '0.5rem' }}>
                  <div style={{
                    padding: '0.5rem',
                    borderBottom: `1px solid ${colors.bgSecondary}`,
                    marginBottom: '0.5rem'
                  }}>
                    <div style={{ fontWeight: '500', fontSize: '0.875rem', color: colors.textPrimary }}>{userName}</div>
                    <div style={{ fontSize: '0.75rem', color: colors.textMuted }}>{userEmail}</div>
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
                      borderRadius: '3px',
                      cursor: 'pointer',
                      fontSize: '0.875rem',
                      color: colors.danger,
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.5rem',
                      transition: 'background 0.2s'
                    }}
                    onMouseOver={(e) => e.target.style.backgroundColor = '#fef2f2'}
                    onMouseOut={(e) => e.target.style.backgroundColor = 'transparent'}
                  >
                    <LogOut size={16} />
                    Sign Out
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </header>

      <div style={{
        maxWidth: '1400px',
        margin: '0 auto',
        padding: '1.5rem',
        display: 'grid',
        gridTemplateColumns: '350px 1fr',
        gap: '1.5rem'
      }}>
        
        {/* Chat History Sidebar */}
        <div className={`sidebar ${showHistory ? '' : 'hidden'}`} style={{ display: showHistory ? 'flex' : 'none', flexDirection: 'column', gap: '1rem' }}>
          <div style={{
            background: 'white',
            border: `1px solid ${colors.borderLight}`,
            borderRadius: '4px',
            boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
            padding: '1.25rem'
          }}>
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginBottom: '1rem'
            }}>
              <span style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                fontSize: '16px',
                fontWeight: '600',
                color: colors.textPrimary
              }}>
                <MessageSquare size={18} />
                Chat History
              </span>
              <button 
                onClick={startNewChat}
                style={{
                  background: colors.accent,
                  color: 'white',
                  border: 'none',
                  borderRadius: '3px',
                  padding: '4px 8px',
                  fontSize: '12px',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                  transition: 'background 0.2s'
                }}
                onMouseEnter={(e) => e.currentTarget.style.background = '#0d3e6b'}
                onMouseLeave={(e) => e.currentTarget.style.background = colors.accent}
              >
                <Plus size={14} />
                New
              </button>
            </div>
            
            <div style={{ maxHeight: '300px', overflowY: 'auto' }}>
              {chatSessions.length === 0 ? (
                <div style={{ padding: '1rem', textAlign: 'center', color: colors.textMuted, fontSize: '0.875rem' }}>
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
                      backgroundColor: currentSessionId === session.id ? '#f0f7ff' : colors.bgSecondary,
                      border: `1px solid ${currentSessionId === session.id ? colors.accent : colors.borderLight}`,
                      borderRadius: '3px',
                      cursor: 'pointer',
                      fontSize: '0.875rem',
                      transition: 'all 0.2s'
                    }}
                  >
                    <div style={{ fontWeight: '500', marginBottom: '0.25rem', color: colors.textPrimary }}>
                      {session.session_name}
                    </div>
                    <div style={{ color: colors.textMuted, fontSize: '0.75rem' }}>
                      {session.message_count} messages • {new Date(session.last_message_at).toLocaleDateString()}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Upload Section */}
          <div style={{
            background: 'white',
            border: `1px solid ${colors.borderLight}`,
            borderRadius: '4px',
            boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
            padding: '1.25rem'
          }}>
            <h3 style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              fontSize: '16px',
              fontWeight: '600',
              color: colors.textPrimary,
              margin: '0 0 1rem 0'
            }}>
              <FolderOpen size={18} />
              Upload Documents
            </h3>
            
            <div style={{
              border: `2px dashed ${colors.borderMedium}`,
              borderRadius: '4px',
              padding: '1.5rem',
              textAlign: 'center',
              cursor: isUploading ? 'not-allowed' : 'pointer',
              transition: 'all 0.2s',
              background: colors.bgSecondary
            }}
            onClick={() => fileInputRef.current?.click()}
            onMouseEnter={(e) => {
              if (!isUploading) {
                e.currentTarget.style.borderColor = colors.accent;
                e.currentTarget.style.background = colors.bgTertiary;
              }
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = colors.borderMedium;
              e.currentTarget.style.background = colors.bgSecondary;
            }}>
              <input
                type="file"
                ref={fileInputRef}
                onChange={handleFileUpload}
                accept=".txt,.pdf,.md,.xlsx,.xls"
                style={{ display: 'none' }}
              />
              <button
                disabled={isUploading}
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  gap: '0.5rem',
                  width: '100%',
                  background: 'none',
                  border: 'none',
                  cursor: 'inherit',
                  color: colors.textSecondary
                }}
              >
                {isUploading ? (
                  <div style={{
                    width: '24px',
                    height: '24px',
                    border: `2px solid ${colors.borderMedium}`,
                    borderTop: `2px solid ${colors.accent}`,
                    borderRadius: '50%',
                    animation: 'spin 1s linear infinite'
                  }}></div>
                ) : (
                  <Upload size={24} />
                )}
                <span style={{ fontSize: '14px', fontWeight: '500' }}>
                  {isUploading ? 'Uploading...' : 'Click to upload'}
                </span>
                <span style={{ fontSize: '12px', color: colors.textMuted }}>
                  TXT, PDF, MD, XLSX files
                </span>
              </button>
            </div>
          </div>

          {/* Uploaded Files with DocumentManager */}
          {uploadedFiles.length > 0 && (
            <DocumentManager 
              documents={uploadedFiles}
              userEmail={userEmail}
              onDocumentDeleted={(docId, filename) => {
                // Show message in chat
                addSystemMessage(`Document "${filename}" has been deleted successfully.`);
                
                // If deleted document was the only one, clear the list
                if (uploadedFiles.length === 1) {
                  setUploadedFiles([]);
                }
              }}
              onRefresh={loadDocuments}
            />
          )}
        </div>
      
        {/* Main Chat Area */}
        <div style={{
          background: 'white',
          borderRadius: '4px',
          boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
          border: `1px solid ${colors.borderLight}`,
          display: 'flex',
          flexDirection: 'column',
          height: '700px'
        }}>
          
          {/* Chat Header */}
          <div style={{
            borderBottom: `1px solid ${colors.borderLight}`,
            padding: '1rem 1.5rem',
            background: colors.bgSecondary
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                fontSize: '18px',
                fontWeight: '600',
                color: colors.textPrimary
              }}>
                <MessageSquare size={20} />
                {currentSessionName}
                {currentSessionId && (
                  <span style={{ fontSize: '0.75rem', color: colors.textMuted, marginLeft: '0.5rem' }}>
                    (Session #{currentSessionId})
                  </span>
                )}
              </div>
              <button
                onClick={() => setShowHistory(!showHistory)}
                style={{
                  background: 'none',
                  border: `1px solid ${colors.borderMedium}`,
                  borderRadius: '3px',
                  padding: '4px 8px',
                  fontSize: '12px',
                  cursor: 'pointer',
                  color: colors.textSecondary,
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                  transition: 'all 0.2s'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = colors.accent;
                  e.currentTarget.style.color = colors.accent;
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = colors.borderMedium;
                  e.currentTarget.style.color = colors.textSecondary;
                }}
              >
                {showHistory ? <X size={14} /> : <Menu size={14} />}
                {showHistory ? 'Hide' : 'Show'} History
              </button>
            </div>
          </div>

          {/* Messages */}
          <div style={{
            flex: 1,
            overflowY: 'auto',
            padding: '1rem'
          }}>
            {messages.length === 0 ? (
              <div style={{
                textAlign: 'center',
                padding: '3rem 1rem',
                color: colors.textMuted
              }}>
                <Search size={48} style={{ marginBottom: '1rem', opacity: 0.3 }} />
                <h3 style={{
                  fontSize: '18px',
                  fontWeight: '500',
                  color: colors.textSecondary,
                  margin: '0 0 0.5rem 0'
                }}>Welcome, {userName}!</h3>
                <p style={{ fontSize: '14px', maxWidth: '400px', margin: '0 auto' }}>
                  {currentSessionId 
                    ? 'Continue your conversation or explore new topics in this session.'
                    : 'Upload documents and ask questions to see the RAG system in action. Try: "What is the main topic?" or "Summarize the key points"'
                  }
                </p>
              </div>
            ) : (
              messages.map((message, index) => (
                <div key={index} style={{
                  display: 'flex',
                  marginBottom: '1rem',
                  justifyContent: message.type === 'user' ? 'flex-end' : 'flex-start'
                }}>
                  {message.type === 'system' ? (
                    <div style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.5rem',
                      padding: '0.75rem 1rem',
                      background: colors.bgSecondary,
                      borderRadius: '4px',
                      border: `1px solid ${colors.borderLight}`,
                      fontSize: '13px',
                      color: colors.textSecondary,
                      width: '100%'
                    }}>
                      <Info size={16} color={colors.warning} />
                      {message.content}
                    </div>
                  ) : (
                    <div style={{
                      maxWidth: '75%',
                      padding: '0.75rem 1rem',
                      borderRadius: '4px',
                      wordWrap: 'break-word',
                      background: message.type === 'user' ? colors.accent : colors.bgSecondary,
                      color: message.type === 'user' ? 'white' : colors.textPrimary,
                      border: message.type === 'assistant' ? `1px solid ${colors.borderLight}` : 'none'
                    }}>
                      
                      {message.type === 'assistant' && (
                        <div style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: '0.5rem',
                          marginBottom: '0.5rem',
                          fontSize: '13px',
                          fontWeight: '500',
                          color: colors.accent
                        }}>
                          <Brain size={16} />
                          <span>AI Response</span>
                          {message.confidence !== undefined && (
                            <span style={{ color: colors.textMuted, fontWeight: 'normal' }}>
                              • Confidence: {(message.confidence * 100).toFixed(1)}%
                            </span>
                          )}
                        </div>
                      )}
                      
                      <div>{message.content}</div>
                      
                      {message.sources && message.sources.length > 0 && (
                        <div style={{
                          marginTop: '0.75rem',
                          paddingTop: '0.75rem',
                          borderTop: `1px solid ${colors.borderLight}`
                        }}>
                          <div style={{
                            fontSize: '12px',
                            fontWeight: '600',
                            marginBottom: '0.5rem',
                            color: colors.textSecondary
                          }}>Sources:</div>
                          <div>
                            {message.sources.map((source, idx) => (
                              <div key={idx} style={{
                                background: colors.bgTertiary,
                                padding: '0.5rem',
                                borderRadius: '3px',
                                marginBottom: '0.5rem',
                                fontSize: '12px'
                              }}>
                                <div style={{
                                  fontWeight: '500',
                                  color: colors.textPrimary,
                                  marginBottom: '0.25rem'
                                }}>{source.source}</div>
                                <div style={{
                                  color: colors.accent,
                                  marginBottom: '0.25rem'
                                }}>
                                  Similarity: {(source.similarity * 100).toFixed(1)}%
                                </div>
                                <div style={{
                                  color: colors.textSecondary,
                                  fontStyle: 'italic'
                                }}>
                                  "{source.content_preview}"
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                      
                      <div style={{
                        fontSize: '11px',
                        marginTop: '0.5rem',
                        opacity: 0.6,
                        color: message.type === 'user' ? 'rgba(255,255,255,0.8)' : colors.textMuted
                      }}>
                        {message.timestamp}
                      </div>
                    </div>
                  )}
                </div>
              ))
            )}
            
            {isLoading && (
              <div style={{
                display: 'flex',
                justifyContent: 'flex-start',
                marginBottom: '1rem'
              }}>
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  padding: '0.75rem 1rem',
                  background: colors.bgSecondary,
                  borderRadius: '4px',
                  border: `1px solid ${colors.borderLight}`,
                  fontSize: '14px',
                  color: colors.textSecondary
                }}>
                  <div style={{
                    width: '16px',
                    height: '16px',
                    border: `2px solid ${colors.borderMedium}`,
                    borderTop: `2px solid ${colors.accent}`,
                    borderRadius: '50%',
                    animation: 'spin 1s linear infinite'
                  }}></div>
                  <span>AI is thinking...</span>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input Area */}
          <div style={{
            borderTop: `1px solid ${colors.borderLight}`,
            padding: '1rem',
            background: colors.bgSecondary
          }}>
            <div style={{
              display: 'flex',
              gap: '0.75rem'
            }}>
              <div style={{ flex: 1 }}>
                <textarea
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder={
                    currentSessionId 
                      ? "Continue your conversation..." 
                      : "Ask a question about your documents..."
                  }
                  style={{
                    width: '100%',
                    padding: '0.75rem',
                    border: `1px solid ${colors.borderMedium}`,
                    borderRadius: '4px',
                    outline: 'none',
                    resize: 'none',
                    fontSize: '14px',
                    fontFamily: 'inherit',
                    transition: 'border-color 0.2s',
                    minHeight: '60px'
                  }}
                  rows={2}
                  disabled={isLoading}
                  onFocus={(e) => e.target.style.borderColor = colors.accent}
                  onBlur={(e) => e.target.style.borderColor = colors.borderMedium}
                />
              </div>
              <button
                onClick={handleSendMessage}
                disabled={!inputValue.trim() || isLoading}
                style={{
                  background: colors.accent,
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  padding: '0 1.5rem',
                  cursor: !inputValue.trim() || isLoading ? 'not-allowed' : 'pointer',
                  transition: 'all 0.2s',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '0.5rem',
                  fontSize: '14px',
                  fontWeight: '500',
                  opacity: !inputValue.trim() || isLoading ? 0.6 : 1
                }}
                onMouseEnter={(e) => {
                  if (inputValue.trim() && !isLoading) {
                    e.currentTarget.style.background = '#0d3e6b';
                  }
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = colors.accent;
                }}
              >
                <Send size={18} />
                Send
              </button>
            </div>
            
            <div style={{
              marginTop: '0.5rem',
              fontSize: '12px',
              color: colors.textMuted,
              display: 'flex',
              justifyContent: 'space-between'
            }}>
              <span>Press Enter to send, Shift+Enter for new line</span>
              {currentSessionId && (
                <span>Session #{currentSessionId}</span>
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
      <ThemeProvider>
        <AppContent />
        <DarkModeToggle />
      </ThemeProvider>
      <style>{`
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      `}</style>
    </AuthProvider>
  );
}

export default App;