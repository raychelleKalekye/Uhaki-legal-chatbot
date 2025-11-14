import React, { useState, useEffect, useLayoutEffect, useRef } from 'react';
import Disclaimer from '../Components/Disclaimer';
import MessageList from '../Components/MessageList';
import MessageInput from '../Components/MessageInput';
import '../Styles/ChatPage.css';

const ChatPage = ({ registerClear }) => {
  const [messages, setMessages] = useState([]);
  const bottomRef = useRef(null);

  const generateId = () => `${Date.now()}-${Math.random().toString(36).substr(2, 5)}`;

  
  useEffect(() => {
    const saved = localStorage.getItem("uhaki_chat_history");
    if (saved) {
      setMessages(JSON.parse(saved));
    } else {
      setMessages([
        { id: generateId(), sender: 'uhaki', text: 'Hello, I’m Uhaki, a legal assistant. How may I help you?' }
      ]);
    }
  }, []);

  
  useEffect(() => {
    if (messages.length > 0) {
      localStorage.setItem("uhaki_chat_history", JSON.stringify(messages));
    }
  }, [messages]);


  useEffect(() => {
    if (registerClear) {
      registerClear.current = () => {
        const confirmClear = window.confirm("Are you sure you want to clear this chat?");
        if (confirmClear) {
          localStorage.removeItem("uhaki_chat_history");
          setMessages([
            { id: generateId(), sender: 'uhaki', text: 'Hello, I’m Uhaki, a legal assistant. How may I help you?' }
          ]);
        }
      };
    }
  }, [registerClear]);

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
      const answer = data.answer || "I'm sorry, I couldn’t find a clear answer from the available acts.";

      
      const uhakiAnswer = {
        id: generateId(),
        sender: 'uhaki',
        text: answer,
      };
      setMessages((prev) => [...prev, uhakiAnswer]);

     
      if (results.length > 0) {
        const sources = results.slice(0, 3).map((r, i) => {
          const act = r.act || '—';
          const section = r.section || '—';
          const snip = (r.text || '').replace(/\s+/g, ' ').slice(0, 200);
          return `#${i + 1} ${act} – ${section}\n${snip}${snip.length === 200 ? '…' : ''}`;
        }).join('\n\n');

        const sourcesMessage = {
          id: generateId(),
          sender: 'uhaki',
          text: `Sources I used:\n\n${sources}`,
        };
        setMessages((prev) => [...prev, sourcesMessage]);
      }

    } catch (error) {
      console.error('Error sending query:', error);
      setMessages((prev) => [
        ...prev,
        {
          id: generateId(),
          sender: 'uhaki',
          text: 'Sorry, there was an error processing your query. Please try again shortly.',
        },
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
