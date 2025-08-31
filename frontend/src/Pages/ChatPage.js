import React, { useState, useEffect, useLayoutEffect, useRef } from 'react';
import Disclaimer from '../Components/Disclaimer';
import MessageList from '../Components/MessageList';
import MessageInput from '../Components/MessageInput';

import '../Styles/ChatPage.css';   
const ChatPage = () => {
  const [messages, setMessages] = useState([]);
  const bottomRef = useRef(null);

  useEffect(() => {
    setMessages([{ sender: 'uhaki', text: 'Hello, I’m Uhaki, a legal assistant. How may I help you?' }]);
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

  const handleSend = (text) => {
    if (!text.trim()) return;
    setMessages((prev) => [...prev, { sender: 'user', text }]);
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
