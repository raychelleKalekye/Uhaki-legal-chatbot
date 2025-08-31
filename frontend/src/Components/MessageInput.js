import React, { useState, useRef, useEffect } from "react";
import "../Styles/MessageInput.css";

const MessageInput = ({ onSend }) => {
  const [value, setValue] = useState("");
  const textareaRef = useRef(null);

  const handleSend = () => {
    const text = value.trim();
    if (!text) return;
    onSend(text);
    setValue("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto"; // reset height after sending
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // Auto resize height on input change
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto"; // reset height first
      const scrollHeight = textareaRef.current.scrollHeight;
      const maxHeight = 150; // matches CSS
      textareaRef.current.style.height =
        scrollHeight > maxHeight ? `${maxHeight}px` : `${scrollHeight}px`;
    }
  }, [value]);

  return (
    <div className="composer">
      <textarea
        ref={textareaRef}
        className="composer-input"
        placeholder="Type your message..."
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        rows={1}
      />
      <button className="send-btn" type="button" onClick={handleSend}>
        ➤
      </button>
    </div>
  );
};

export default MessageInput;
