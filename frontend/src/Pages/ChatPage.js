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

      const data = await response.json();

     
      const botMessage = {
        id: generateId(),
        sender: 'uhaki',
        text: `Predicted Act: ${data.predicted_act} (confidence: ${data.confidence})`
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
