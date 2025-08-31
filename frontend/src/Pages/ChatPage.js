import React, { useState, useEffect } from 'react';
import ChatHeader from '../Components/ChatHeader';
import Disclaimer from '../Components/Disclaimer';
import MessageList from '../Components/MessageList';
import MessageInput from '../Components/MessageInput';

const ChatPage = () => {
  const [messages, setMessages] = useState([]);

  
  useEffect(() => {
    setMessages([
      { sender: "uhaki", text: "Hello, I’m Uhaki, a legal assistant. How may I help you?" }
    ]);
  }, []);

 
  const handleSend = (text) => {
    if (!text.trim()) return;
    setMessages([...messages, { sender: "user", text }]);
  };

  return (
    <div className='ChatPage'>
      <ChatHeader />
      <MessageList messages={messages} />
      <MessageInput onSend={handleSend} />
      <Disclaimer />
    </div>
  );
};

export default ChatPage;
