import React, { useState, useEffect, useLayoutEffect, useRef } from 'react';
import Disclaimer from '../Components/Disclaimer';
import MessageList from '../Components/MessageList';
import MessageInput from '../Components/MessageInput';
import '../Styles/ChatPage.css';

const ChatPage = () => {
  const [messages, setMessages] = useState([]);
  const bottomRef = useRef(null);

 
  const generateId = () => `${Date.now()}-${Math.random().toString(36).substr(2, 5)}`;

  useEffect(() => {
    setMessages([{
      id: generateId(),
      sender: 'uhaki',
      text: 'Hello, I’m Uhaki, a legal assistant. How may I help you?'
    }]);
  }, []);

  useLayoutEffect(() => {
    const setBBHeight = () => {
      const h = bottomRef.current?.offsetHeight || 0;
      document.documentElement.style.setProperty('--bb-h', `${h}px`);
    };
    setBBHeight();
    window.addEventListener('resize', setBBHeight);
    return () => window.removeEventListener('resize', setBBHeight);
  }, []);

  const handleSend = async (text) => {
  if (!text.trim()) return;

  const userMessage = { id: generateId(), sender: 'user', text };
  setMessages((prev) => [...prev, userMessage]);

  try {
    const response = await fetch('http://localhost:5000/askQuery', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },

      body: JSON.stringify({ query: text }),
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const data = await response.json();

    const results = Array.isArray(data.top_results) ? data.top_results : [];
    if (results.length === 0) {
      setMessages((prev) => [
        ...prev,
        {
          id: generateId(),
          sender: 'uhaki',
          text: "I couldn't find a relevant section. Try rephrasing or name the Act, e.g., '… under the Employment Act'.",
        },
      ]);
      return;
    }

    const top = results.slice(0, 3).map((r, i) => {
      const m = r.metadata || {};
      const act = m.act || '—';
      const section = m.section || '—';
      const score = (r.score != null) ? ` (score ${r.score.toFixed(3)})` : '';
      const snip = (r.text || '').replace(/\s+/g, ' ').slice(0, 300);
      return `#${i + 1} ${act} – ${section}${score}\n${snip}${snip.length === 300 ? '…' : ''}`;
    }).join('\n\n');

    const botMessage = {
      id: generateId(),
      sender: 'uhaki',
      text:
        (data.act_filter ? `Act filter: ${data.act_filter}\n\n` : '') +
        top +
        `\n\n(use “act: <Act Name>” in your question to filter results)`,
    };

    setMessages((prev) => [...prev, botMessage]);

  } catch (error) {
    console.error('Error sending query:', error);
    setMessages((prev) => [
      ...prev,
      { id: generateId(), sender: 'uhaki', text: 'Sorry, there was an error processing your query.' },
    ]);
  }
};


  return (
    <div className="ChatPage">
      <main className="ChatScroll">
        <MessageList messages={messages} />
      </main>

      <div className="BottomBar" ref={bottomRef}>
        <div className="BottomInner">
          <MessageInput onSend={handleSend} />
          <div className="Disclaimer"><Disclaimer /></div>
        </div>
      </div>
    </div>
  );
};

export default ChatPage;
