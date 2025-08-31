import React, { useEffect, useRef } from "react";
import '../Styles/MessageList.css'
const MessageList = ({ messages = [], isTyping = false }) => {
  const listRef = useRef(null);

  
  useEffect(() => {
    if (listRef.current) {
      listRef.current.scrollTop = listRef.current.scrollHeight;
    }
  }, [messages, isTyping]);

  return (
    <div ref={listRef} className="message-list-container">
      {messages.map((m) => (
        <div
          key={m.id}
          className={`bubble ${m.role === "assistant" ? "assistant" : "user"}`}
        >
          <div className="bubble-text">{m.text}</div>
          <div className="bubble-meta">{m.time}</div>
        </div>
      ))}

      {isTyping && (
        <div className="bubble assistant">
          <div className="typing">
            <span className="dot" />
            <span className="dot" />
            <span className="dot" />
          </div>
        </div>
      )}
    </div>
  );
};

export default MessageList;
