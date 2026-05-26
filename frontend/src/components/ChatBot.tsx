import React, { useState, useEffect, useRef } from 'react';
import './ChatBot.css';

interface Message {
  id: string;
  text: string;
  sender: 'user' | 'bot';
  timestamp: Date;
}

interface ChatBotProps {
  analyzedFiles?: Record<string, any>;
}

interface SamplePrompts {
  [category: string]: string[];
}

const ChatBot: React.FC<ChatBotProps> = ({ analyzedFiles = {} }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputText, setInputText] = useState('');
  const [loading, setLoading] = useState(false);
  const [sessionId] = useState(() => `session-${Date.now()}`);
  const [showPrompts, setShowPrompts] = useState(true);
  const [samplePrompts, setSamplePrompts] = useState<SamplePrompts>({});
  const [suggestedPrompts, setSuggestedPrompts] = useState<string[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    if (isOpen) {
      loadSamplePrompts();
      if (messages.length === 0) {
        addBotMessage(
          "👋 Hi! I'm your Performance Analysis AI Assistant. I can help you:\n\n" +
          "📊 Understand test results and grades\n" +
          "🔍 Identify performance bottlenecks\n" +
          "💡 Get improvement recommendations\n" +
          "📈 Compare metrics against targets\n" +
          "🎯 Analyze critical issues\n\n" +
          "Select a suggested question below or type your own!"
        );
      }
    }
  }, [isOpen]);

  const loadSamplePrompts = async () => {
    try {
      const response = await fetch('http://localhost:8010/api/chat/sample-prompts');
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
    setShowPrompts(false);

    try {
      const fileIds = Object.keys(analyzedFiles);

      const response = await fetch('http://localhost:8010/api/chat', {
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
    <>
      {/* Chatbot Toggle Button */}
      <button
        className={`chatbot-toggle ${isOpen ? 'open' : ''}`}
        onClick={() => setIsOpen(!isOpen)}
        title="AI Performance Assistant"
      >
        {isOpen ? '✕' : '🤖'}
        {!isOpen && <span className="chatbot-badge">{Object.keys(analyzedFiles).length}</span>}
      </button>

      {/* Chatbot Window */}
      {isOpen && (
        <div className="chatbot-window">
          <div className="chatbot-header">
            <div>
              <h3>🤖 Performance AI Assistant</h3>
              <p className="header-subtitle">Intelligent Analysis & Insights</p>
            </div>
            <button className="close-chat" onClick={() => setIsOpen(false)}>✕</button>
          </div>

          <div className="chatbot-messages">
            {messages.length === 0 || showPrompts ? (
              <div className="welcome-section">
                <div className="welcome-icon">🎯</div>
                <h4>Ask me anything about your performance tests!</h4>
                
                {/* Quick Suggested Prompts */}
                <div className="quick-prompts">
                  <h5>🚀 Quick Questions:</h5>
                  <div className="suggested-questions">
                    {suggestedPrompts.slice(0, 6).map((prompt, index) => (
                      <button
                        key={index}
                        className="suggested-question quick"
                        onClick={() => handlePromptClick(prompt)}
                      >
                        {prompt}
                      </button>
                    ))}
                  </div>
                </div>

                {/* View All Prompts */}
                <button 
                  className="view-all-prompts-btn"
                  onClick={() => setShowPrompts(!showPrompts)}
                >
                  {showPrompts ? '📚 View All Sample Questions' : '🔙 Back to Quick Questions'}
                </button>

                {/* All Prompts by Category */}
                {showPrompts && Object.keys(samplePrompts).length > 0 && (
                  <div className="all-prompts-section">
                    <h5>📚 All Available Questions by Category:</h5>
                    {Object.entries(promptCategories).map(([category, prompts]) => (
                      prompts.length > 0 && (
                        <div key={category} className="prompt-category">
                          <h6>{category}</h6>
                          <div className="category-prompts">
                            {prompts.slice(0, 4).map((prompt, idx) => (
                              <button
                                key={idx}
                                className="suggested-question category"
                                onClick={() => handlePromptClick(prompt)}
                              >
                                {prompt}
                              </button>
                            ))}
                          </div>
                        </div>
                      )
                    ))}
                  </div>
                )}
              </div>
            ) : (
              <>
                {messages.map(message => (
                  <div key={message.id} className={`message ${message.sender}`}>
                    <div className="message-avatar">
                      {message.sender === 'user' ? '👤' : '🤖'}
                    </div>
                    <div className="message-content">
                      <div className="message-text">
                        {message.text.split('\n').map((line, i) => (
                          <React.Fragment key={i}>
                            {line}
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
              </>
            )}
            <div ref={messagesEndRef} />
          </div>

          <div className="chatbot-actions">
            {messages.length > 0 && (
              <>
                <button 
                  className="action-btn"
                  onClick={() => {
                    setMessages([]);
                    setShowPrompts(true);
                  }}
                  title="Clear chat"
                >
                  🗑️ Clear
                </button>
                <button 
                  className="action-btn"
                  onClick={() => setShowPrompts(!showPrompts)}
                  title="Toggle prompts"
                >
                  {showPrompts ? '💬' : '❓'} {showPrompts ? 'Hide' : 'Show'} Prompts
                </button>
              </>
            )}
          </div>

          <div className="chatbot-input">
            <textarea
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Ask about performance, errors, recommendations, grades..."
              disabled={loading}
              rows={2}
            />
            <button
              onClick={handleSend}
              disabled={loading || !inputText.trim()}
              className="send-button"
              title="Send message"
            >
              {loading ? '⏳' : '📤'}
            </button>
          </div>

          {Object.keys(analyzedFiles).length > 0 && (
            <div className="context-info">
              💡 Analyzing {Object.keys(analyzedFiles).length} file(s) - 
              {Object.values(analyzedFiles).filter((f: any) => f.category === 'jmeter').length} JMeter, 
              {Object.values(analyzedFiles).filter((f: any) => f.category === 'web_vitals').length} Web Vitals,
              {Object.values(analyzedFiles).filter((f: any) => f.category === 'ui_performance').length} UI Performance
            </div>
          )}
        </div>
      )}
    </>
  );
};

export default ChatBot;
