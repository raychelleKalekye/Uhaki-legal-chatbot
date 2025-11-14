import React, { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import "../Styles/MessageList.css";
import robotLogo from "../Assets/robotlogo.webp";

const MessageList = ({ messages = [], isTyping = false }) => {
  const listRef = useRef(null);
  const [sourcesModal, setSourcesModal] = useState(null);

  useEffect(() => {
    if (listRef.current) {
      listRef.current.scrollTop = listRef.current.scrollHeight;
    }
  }, [messages, isTyping]);

  const openSourcesModal = (message) => {
    if (message.sources && message.sources.length > 0) {
      setSourcesModal(message);
    }
  };

  const closeModal = () => setSourcesModal(null);

  return (
    <div ref={listRef} className="message-list-container">
      {messages.map((m) => {
        const hasSources = Array.isArray(m.sources) && m.sources.length > 0;
        return (
          <div key={m.id} className={`message-row ${m.sender}`}>
            {m.sender === "uhaki" && (
              <img src={robotLogo} alt="Uhaki" className="avatar" />
            )}

            <div className="message-content">
              <div className={`bubble ${m.sender}`}>
                <div className="bubble-text">
                  <ReactMarkdown
                    skipHtml
                    components={{
                      a: ({ node, ...props }) => (
                        <a {...props} target="_blank" rel="noreferrer" />
                      )
                    }}
                  >
                    {m.text || ""}
                  </ReactMarkdown>
                </div>
                {m.time && <div className="bubble-meta">{m.time}</div>}
              </div>

              {m.sender === "uhaki" && (
                <div className="bubble-actions">
                  <button
                    type="button"
                    className="copy-btn"
                    onClick={(e) => {
                      navigator.clipboard.writeText(m.text || "");
                      const btn = e.currentTarget;
                      const oldText = btn.innerText;
                      btn.innerText = "Copied!";
                      setTimeout(() => (btn.innerText = oldText), 1000);
                    }}
                  >
                    Copy
                  </button>
                    {hasSources && (
                      <button
                        type="button"
                        className="sources-link"
                        onClick={() => openSourcesModal(m)}
                      >
                      Sources used
                    </button>
                  )}
                </div>
              )}
            </div>
          </div>
        );
      })}

      {isTyping && (
        <div className="message-row uhaki">
          <img src={robotLogo} alt="Uhaki" className="avatar" />
          <div className="bubble typing-bubble">
            <div className="typing">
              <span className="dot" />
              <span className="dot" />
              <span className="dot" />
            </div>
          </div>
        </div>
      )}

      {sourcesModal && (
        <div className="sources-overlay" onClick={closeModal}>
          <div
            className="sources-modal"
            onClick={(e) => e.stopPropagation()}
          >
            <button className="modal-close" onClick={closeModal} aria-label="Close">
              &times;
            </button>
            <h3>Sources used</h3>
            <ol>
              {sourcesModal.sources.map((src, idx) => (
                <li key={`${sourcesModal.id}-modal-${idx}`}>
                  <div className="source-title">
                    {src.act || "N/A"} - {src.section || "N/A"}
                  </div>
                  {src.snippet && (
                    <p>
                      {src.snippet}
                      {src.snippet.length === 200 ? "..." : ""}
                    </p>
                  )}
                </li>
              ))}
            </ol>
          </div>
        </div>
      )}
    </div>
  );
};

export default MessageList;
