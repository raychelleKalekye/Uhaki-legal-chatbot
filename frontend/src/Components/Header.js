import React from 'react';
import { useLocation } from 'react-router-dom';
import logo from '../Assets/logo.png';
import '../Styles/Header.css';

const Header = ({ onClearChat }) => {
  const location = useLocation();
  const onChatPage = location.pathname === '/ChatPage';

  return (
    <div className='header'>
      <div className='heading'>
        <img src={logo} alt='logo' />
        <h1>Uhaki</h1>
      </div>

      {onChatPage && (
        <button className="clear-btn" onClick={onClearChat}>
           Clear Chat
        </button>
      )}
    </div>
  );
};

export default Header;
