import React from 'react'
import robotLogo from '../Assets/robotlogo.webp';
import '../Styles/ChatHeader.css';
const ChatHeader = () => {
  return (
  <div className="chatHeader">
      <img src={robotLogo} alt='robot logo'/>
      <strong>Uhaki Legal Assistant</strong>
      
    </div>
  )
}

export default ChatHeader

