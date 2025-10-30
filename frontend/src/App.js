import React, { useRef } from 'react';
import Header from './Components/Header';
import './App.css';
import ChatPage from './Pages/ChatPage';
import LandinPage from './Pages/LandinPage';
import { Routes, Route, useLocation } from 'react-router-dom';

function App() {
  const location = useLocation();
  const path = location.pathname;
  const showHeader = path === '/ChatPage';

  // A reference to trigger clearChat inside ChatPage
  const chatRef = useRef();

  const handleClearChat = () => {
    if (chatRef.current) {
      chatRef.current(); // trigger ChatPage's clear function
    }
  };

  return (
    <div className="App">
      {showHeader && <Header onClearChat={handleClearChat} />}
      <Routes>
        <Route path="/" element={<LandinPage />} />
        <Route path="/ChatPage" element={<ChatPage registerClear={chatRef} />} />
      </Routes>
    </div>
  );
}

export default App;
