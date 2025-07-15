// frontend/src/components/Auth.js
import React, { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { Brain, Mail, Lock, User, LogIn, UserPlus, Chrome } from 'lucide-react';

const Auth = () => {
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState({ text: '', type: '' });

  const { signIn, signUp, signInWithGoogle } = useAuth();

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

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setMessage({ text: '', type: '' });

    try {
      let result;
      if (isLogin) {
        result = await signIn(email, password);
      } else {
        result = await signUp(email, password, { name });
      }

      if (result.error) {
        setMessage({
          text: result.error.message || 'An error occurred',
          type: 'error'
        });
      } else {
        if (!isLogin) {
          setMessage({
            text: 'Check your email for confirmation link!',
            type: 'success'
          });
        }
      }
    } catch (error) {
      setMessage({
        text: error.message || 'An unexpected error occurred',
        type: 'error'
      });
    } finally {
      setLoading(false);
    }
  };

  const handleGoogleSignIn = async () => {
    setLoading(true);
    setMessage({ text: '', type: '' });

    try {
      const { error } = await signInWithGoogle();
      if (error) {
        setMessage({
          text: error.message || 'Google sign in failed',
          type: 'error'
        });
      }
    } catch (error) {
      setMessage({
        text: error.message || 'An unexpected error occurred',
        type: 'error'
      });
    } finally {
      setLoading(false);
    }
  };

  const inputStyle = {
    width: '100%',
    padding: '0.75rem',
    border: `1px solid ${colors.borderMedium}`,
    borderRadius: '4px',
    fontSize: '14px',
    outline: 'none',
    transition: 'border-color 0.2s',
    fontFamily: 'inherit',
    backgroundColor: colors.bgPrimary
  };

  const labelStyle = {
    display: 'block',
    fontSize: '14px',
    fontWeight: '500',
    color: colors.textPrimary,
    marginBottom: '0.5rem'
  };

  return (
    <div style={{
      minHeight: '100vh',
      background: colors.bgSecondary,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '1rem'
    }}>
      <div style={{
        background: colors.bgPrimary,
        borderRadius: '4px',
        boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)',
        padding: '2.5rem',
        width: '100%',
        maxWidth: '420px',
        border: `1px solid ${colors.borderLight}`
      }}>
        {/* Header */}
        <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
          <div style={{
            width: '60px',
            height: '60px',
            background: colors.accent,
            borderRadius: '4px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            margin: '0 auto 1rem'
          }}>
            <Brain size={32} color="white" />
          </div>
          <h1 style={{
            fontSize: '24px',
            fontWeight: '600',
            color: colors.textPrimary,
            marginBottom: '0.5rem',
            letterSpacing: '-0.5px'
          }}>
            {isLogin ? 'Welcome Back' : 'Create Account'}
          </h1>
          <p style={{
            color: colors.textSecondary,
            fontSize: '14px'
          }}>
            {isLogin 
              ? 'Sign in to access your document intelligence platform' 
              : 'Join our enterprise RAG system'
            }
          </p>
        </div>

        {/* Message */}
        {message.text && (
          <div style={{
            padding: '0.75rem',
            borderRadius: '4px',
            marginBottom: '1rem',
            backgroundColor: message.type === 'error' ? '#fee' : '#efe',
            color: message.type === 'error' ? colors.danger : colors.success,
            border: `1px solid ${message.type === 'error' ? '#fcc' : '#cfc'}`,
            fontSize: '14px',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem'
          }}>
            {message.text}
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} style={{ marginBottom: '1.5rem' }}>
          {!isLogin && (
            <div style={{ marginBottom: '1rem' }}>
              <label style={labelStyle}>
                <User size={14} style={{ display: 'inline', marginRight: '4px' }} />
                Full Name
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required={!isLogin}
                style={inputStyle}
                onFocus={(e) => e.target.style.borderColor = colors.accent}
                onBlur={(e) => e.target.style.borderColor = colors.borderMedium}
                placeholder="John Doe"
              />
            </div>
          )}

          <div style={{ marginBottom: '1rem' }}>
            <label style={labelStyle}>
              <Mail size={14} style={{ display: 'inline', marginRight: '4px' }} />
              Email Address
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              style={inputStyle}
              onFocus={(e) => e.target.style.borderColor = colors.accent}
              onBlur={(e) => e.target.style.borderColor = colors.borderMedium}
              placeholder="john@company.com"
            />
          </div>

          <div style={{ marginBottom: '1.5rem' }}>
            <label style={labelStyle}>
              <Lock size={14} style={{ display: 'inline', marginRight: '4px' }} />
              Password
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              style={inputStyle}
              onFocus={(e) => e.target.style.borderColor = colors.accent}
              onBlur={(e) => e.target.style.borderColor = colors.borderMedium}
              placeholder={isLogin ? "Enter your password" : "Create a strong password"}
              minLength={isLogin ? undefined : 6}
            />
            {!isLogin && (
              <p style={{
                fontSize: '12px',
                color: colors.textMuted,
                marginTop: '0.25rem'
              }}>
                Minimum 6 characters required
              </p>
            )}
          </div>

          <button
            type="submit"
            disabled={loading}
            style={{
              width: '100%',
              backgroundColor: loading ? colors.textMuted : colors.accent,
              color: 'white',
              fontWeight: '500',
              padding: '0.75rem',
              borderRadius: '4px',
              border: 'none',
              fontSize: '14px',
              cursor: loading ? 'not-allowed' : 'pointer',
              transition: 'background-color 0.2s',
              marginBottom: '1rem',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '0.5rem'
            }}
            onMouseEnter={(e) => {
              if (!loading) e.target.style.backgroundColor = '#0d3e6b';
            }}
            onMouseLeave={(e) => {
              if (!loading) e.target.style.backgroundColor = colors.accent;
            }}
          >
            {loading ? (
              <>
                <div style={{
                  width: '16px',
                  height: '16px',
                  border: '2px solid white',
                  borderTop: '2px solid transparent',
                  borderRadius: '50%',
                  animation: 'spin 0.8s linear infinite'
                }}></div>
                Processing...
              </>
            ) : (
              <>
                {isLogin ? <LogIn size={16} /> : <UserPlus size={16} />}
                {isLogin ? 'Sign In' : 'Create Account'}
              </>
            )}
          </button>
        </form>

        {/* Divider */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          marginBottom: '1.5rem'
        }}>
          <div style={{
            flex: 1,
            height: '1px',
            background: colors.borderLight
          }}></div>
          <span style={{
            padding: '0 1rem',
            color: colors.textMuted,
            fontSize: '13px'
          }}>
            or continue with
          </span>
          <div style={{
            flex: 1,
            height: '1px',
            background: colors.borderLight
          }}></div>
        </div>

        {/* Google Sign In */}
        <button
          onClick={handleGoogleSignIn}
          disabled={loading}
          style={{
            width: '100%',
            backgroundColor: colors.bgPrimary,
            color: colors.textPrimary,
            fontWeight: '500',
            padding: '0.75rem',
            borderRadius: '4px',
            border: `1px solid ${colors.borderMedium}`,
            fontSize: '14px',
            cursor: loading ? 'not-allowed' : 'pointer',
            transition: 'all 0.2s',
            marginBottom: '1.5rem',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '0.5rem'
          }}
          onMouseEnter={(e) => {
            if (!loading) {
              e.target.style.backgroundColor = colors.bgSecondary;
              e.target.style.borderColor = colors.accent;
            }
          }}
          onMouseLeave={(e) => {
            e.target.style.backgroundColor = colors.bgPrimary;
            e.target.style.borderColor = colors.borderMedium;
          }}
        >
          <Chrome size={18} />
          Continue with Google
        </button>

        {/* Toggle Login/Register */}
        <div style={{ textAlign: 'center' }}>
          <span style={{ color: colors.textSecondary, fontSize: '14px' }}>
            {isLogin ? "Don't have an account? " : "Already have an account? "}
          </span>
          <button
            type="button"
            onClick={() => {
              setIsLogin(!isLogin);
              setMessage({ text: '', type: '' });
            }}
            style={{
              color: colors.accent,
              fontWeight: '500',
              fontSize: '14px',
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              textDecoration: 'none',
              transition: 'color 0.2s'
            }}
            onMouseEnter={(e) => e.target.style.textDecoration = 'underline'}
            onMouseLeave={(e) => e.target.style.textDecoration = 'none'}
          >
            {isLogin ? 'Sign up' : 'Sign in'}
          </button>
        </div>
      </div>

      <style jsx>{`
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
};

export default Auth;