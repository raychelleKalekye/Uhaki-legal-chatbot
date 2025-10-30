import React, { useEffect, useRef } from "react";
import "../Styles/MessageList.css";
import robotLogo from "../Assets/robotlogo.webp";

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
        <div key={m.id} className={`message-row ${m.sender}`}>
          {m.sender === "uhaki" && (
            <img src={robotLogo} alt="Uhaki" className="avatar" />
          )}

          <div className={`bubble ${m.sender}`}>
            <div className="bubble-text">{m.text}</div>
            {m.time && <div className="bubble-meta">{m.time}</div>}
          </div>

          
          {m.sender === "uhaki" && (
            <button
              className="copy-btn"
             onClick={(e) => {
                navigator.clipboard.writeText(m.text);
                const btn = e.currentTarget;
                const oldText = btn.innerText;
                btn.innerText = " Copied!";
                setTimeout(() => (btn.innerText = oldText), 1000);
              }}


            >
              📋 Copy
            </button>
          )}
        </div>
      ))}

      {isTyping && (
        <div className="message-row uhaki">
          <img src={robotLogo} alt="Uhaki" className="avatar" />
          <div className="bubble uhaki">
            <div className="typing">
              <span className="dot" />
              <span className="dot" />
              <span className="dot" />
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default MessageList;
