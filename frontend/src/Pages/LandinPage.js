import React from "react";
import { useNavigate } from "react-router-dom";
import Outline from "../Assets/Outline.png";
import "../Styles/LandinPage.css";

const LandinPage = () => {
  const navigate = useNavigate();

  const goToChat = () => {
    navigate("/ChatPage");
  };

  return (
    <main className="lp">
      <section className="lp-left">
        <div className="lp-mapWrap">
          <img src={Outline} alt="Kenya outline" className="lp-map" />
          <span className="lp-brand">Uhaki</span>
          <div className="lp-glow" aria-hidden="true" />
        </div>
      </section>

      <section className="lp-right">
        <h1 className="lp-title">Legal Assistant System</h1>
        <p className="lp-sub">
          Uhaki is designed to make access to legal information simple and
          accessible. It provides general legal guidance and helps users
          navigate laws with ease.
        </p>

        <button className="lp-cta" onClick={goToChat}>
          <span>Start Chat</span>
          <span className="lp-ctaArrow" aria-hidden="true">›</span>
        </button>
      </section>
      <section className="lp-copyRightS">
          <p className="lp-copyRightP">
          © 2025 Uhaki Legal Assistant System. All rights reserved.
        </p>
      </section>
    </main>
  );
};

export default LandinPage;
