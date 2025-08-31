import React from 'react'
import ChatHeader from '../Components/ChatHeader';
import Disclaimer from '../Components/Disclaimer';
import MessageList from '../Components/MessageList';
import MessageInput from '../Components/MessageInput';
const ChatPage = () => {
  return (
    <div className='ChatPage'>
      <ChatHeader/>
      <MessageList/>
      <MessageInput/>
      <Disclaimer/>
    </div>
  )
}

export default ChatPage
