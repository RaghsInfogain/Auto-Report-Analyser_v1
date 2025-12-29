import React, { useState, useEffect, useRef } from 'react';
import './AIChatPage.css';

interface Message {
  id: string;
  text: string;
  sender: 'user' | 'bot';
  timestamp: Date;
}

interface SamplePrompts {
  [category: string]: string[];
}

const AIChatPage: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputText, setInputText] = useState('');
  const [loading, setLoading] = useState(false);
  const [sessionId] = useState(() => `session-${Date.now()}`);
  const [samplePrompts, setSamplePrompts] = useState<SamplePrompts>({});
  const [suggestedPrompts, setSuggestedPrompts] = useState<string[]>([]);
  const [analyzedFiles, setAnalyzedFiles] = useState<any[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    loadSamplePrompts();
    loadAnalyzedFiles();
    
    // Welcome message
    addBotMessage(
      "👋 **Welcome to the AI Performance Assistant!**\n\n" +
      "I can help you analyze your performance test results. Here's what I can do:\n\n" +
      "📊 **Understand test results and grades**\n" +
      "🔍 **Identify performance bottlenecks**\n" +
      "💡 **Get improvement recommendations**\n" +
      "📈 **Compare metrics against targets**\n" +
      "🎯 **Analyze critical issues**\n\n" +
      "**Quick Tips:**\n" +
      "• Click any suggested question below\n" +
      "• Type your own questions in natural language\n" +
      "• Browse categories for specific topics\n" +
      "• I analyze all your uploaded files together\n\n" +
      "**Try asking:**\n" +
      "• \"What's the overall performance grade?\"\n" +
      "• \"Show me the error rates\"\n" +
      "• \"Give me recommendations\"\n" +
      "• \"What are the critical issues?\""
    );
  }, []);

  const loadSamplePrompts = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/chat/sample-prompts');
      if (response.ok) {
        const data = await response.json();
        setSamplePrompts(data.all_prompts || {});
        setSuggestedPrompts(data.suggested_prompts || []);
      }
    } catch (error) {
      console.error('Error loading prompts:', error);
      // Fallback prompts
      setSuggestedPrompts([
        "What's the overall performance grade?",
        "Show me the error rates",
        "What are the response times?",
        "Give me recommendations",
        "What are the critical issues?",
        "Compare current vs targets"
      ]);
    }
  };

  const loadAnalyzedFiles = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/files');
      if (response.ok) {
        const data = await response.json();
        const filesWithAnalysis = data.files?.filter((f: any) => f.analysis_id) || [];
        setAnalyzedFiles(filesWithAnalysis);
      }
    } catch (error) {
      console.error('Error loading files:', error);
    }
  };

  const addBotMessage = (text: string) => {
    const newMessage: Message = {
      id: `msg-${Date.now()}`,
      text,
      sender: 'bot',
      timestamp: new Date()
    };
    setMessages(prev => [...prev, newMessage]);
  };

  const addUserMessage = (text: string) => {
    const newMessage: Message = {
      id: `msg-${Date.now()}`,
      text,
      sender: 'user',
      timestamp: new Date()
    };
    setMessages(prev => [...prev, newMessage]);
  };

  const handleSend = async () => {
    if (!inputText.trim()) return;

    const userMessage = inputText;
    addUserMessage(userMessage);
    setInputText('');
    setLoading(true);

    try {
      const fileIds = analyzedFiles.map(f => f.id);

      const response = await fetch('http://localhost:8000/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          message: userMessage,
          session_id: sessionId,
          file_ids: fileIds
        })
      });

      if (response.ok) {
        const data = await response.json();
        addBotMessage(data.response);
      } else {
        addBotMessage("❌ Sorry, I encountered an error. Please try again or rephrase your question.");
      }
    } catch (error) {
      console.error('Chat error:', error);
      addBotMessage("❌ Sorry, I'm having trouble connecting. Please ensure the backend is running.");
    } finally {
      setLoading(false);
    }
  };

  const handlePromptClick = (prompt: string) => {
    setInputText(prompt);
    setTimeout(() => handleSend(), 100);
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleClearChat = () => {
    if (window.confirm('Clear all messages?')) {
      setMessages([]);
      loadSamplePrompts();
    }
  };

  const promptCategories = {
    "📊 Overview & Summary": samplePrompts.overview || [],
    "⚡ Response Times": samplePrompts.response_times || [],
    "❌ Errors & Failures": samplePrompts.errors || [],
    "🔴 Critical Issues": samplePrompts.performance_issues || [],
    "💡 Recommendations": samplePrompts.recommendations || [],
    "📈 Comparisons": samplePrompts.comparisons || [],
    "💰 Business Impact": samplePrompts.business_impact || [],
    "📊 Specific Metrics": samplePrompts.specific_metrics || [],
  };

  return (
    <div className="ai-chat-page">
      <div className="chat-header">
        <div className="header-content">
          <h1>🤖 AI Performance Assistant</h1>
          <p>Intelligent analysis and insights for your performance tests</p>
        </div>
        <div className="header-stats">
          <div className="stat-card">
            <span className="stat-icon">📁</span>
            <div className="stat-info">
              <span className="stat-value">{analyzedFiles.length}</span>
              <span className="stat-label">Analyzed Files</span>
            </div>
          </div>
          <div className="stat-card">
            <span className="stat-icon">💬</span>
            <div className="stat-info">
              <span className="stat-value">{messages.length}</span>
              <span className="stat-label">Messages</span>
            </div>
          </div>
        </div>
      </div>

      <div className="chat-container">
        {/* Sidebar with sample prompts */}
        <aside className="prompts-sidebar">
          <h3>📚 Sample Questions</h3>
          
          <div className="quick-prompts-section">
            <h4>🚀 Quick Start</h4>
            <div className="prompt-list">
              {suggestedPrompts.slice(0, 6).map((prompt, index) => (
                <button
                  key={index}
                  className="prompt-button quick"
                  onClick={() => handlePromptClick(prompt)}
                  disabled={loading}
                >
                  {prompt}
                </button>
              ))}
            </div>
          </div>

          <div className="categories-section">
            <h4>📋 By Category</h4>
            {Object.entries(promptCategories).map(([category, prompts]) => (
              prompts.length > 0 && (
                <div key={category} className="category-group">
                  <h5>{category}</h5>
                  <div className="prompt-list">
                    {prompts.slice(0, 3).map((prompt, idx) => (
                      <button
                        key={idx}
                        className="prompt-button category"
                        onClick={() => handlePromptClick(prompt)}
                        disabled={loading}
                      >
                        {prompt}
                      </button>
                    ))}
                  </div>
                </div>
              )
            ))}
          </div>
        </aside>

        {/* Main chat area */}
        <main className="chat-main">
          <div className="messages-container">
            {messages.map(message => (
              <div key={message.id} className={`message ${message.sender}`}>
                <div className="message-avatar">
                  {message.sender === 'user' ? '👤' : '🤖'}
                </div>
                <div className="message-content">
                  <div className="message-text">
                    {message.text.split('\n').map((line, i) => (
                      <React.Fragment key={i}>
                        {line.startsWith('**') && line.endsWith('**') ? (
                          <strong>{line.slice(2, -2)}</strong>
                        ) : line.startsWith('• ') ? (
                          <div className="bullet-point">{line}</div>
                        ) : (
                          line
                        )}
                        {i < message.text.split('\n').length - 1 && <br />}
                      </React.Fragment>
                    ))}
                  </div>
                  <div className="message-time">
                    {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </div>
                </div>
              </div>
            ))}
            {loading && (
              <div className="message bot">
                <div className="message-avatar">🤖</div>
                <div className="message-content">
                  <div className="typing-indicator">
                    <span></span>
                    <span></span>
                    <span></span>
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          <div className="chat-input-container">
            <div className="input-actions">
              <button
                onClick={handleClearChat}
                className="action-button"
                disabled={messages.length === 0}
                title="Clear chat history"
              >
                🗑️ Clear
              </button>
              <button
                onClick={loadAnalyzedFiles}
                className="action-button"
                title="Refresh analyzed files"
              >
                🔄 Refresh
              </button>
            </div>
            <div className="input-wrapper">
              <textarea
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Ask about performance, errors, recommendations, grades... (Press Enter to send)"
                disabled={loading}
                rows={3}
              />
              <button
                onClick={handleSend}
                disabled={loading || !inputText.trim()}
                className="send-button"
                title="Send message"
              >
                {loading ? '⏳' : '📤'} Send
              </button>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
};

export default AIChatPage;












