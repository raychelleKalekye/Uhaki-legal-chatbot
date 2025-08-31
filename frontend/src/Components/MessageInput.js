import React, { useState } from "react";
import "../Styles/MessageInput.css";

const MessageInput = ({ onSend }) => {
  const [value, setValue] = useState("");

  const handleSend = () => {
    const text = value.trim();
    if (!text) return;
    onSend(text);
    setValue("");
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="composer">
      <textarea
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
