import React from 'react';
import logo from '../../public/ai-faq-college-chat-bot-logo.svg';

export function WelcomeHero({ onSelectPrompt }) {
  return (
    <div className="welcome-hero">
      <img
        src={logo}
        alt="AI FAQ College Chat Bot logo"
        className="welcome-logo"
      />

      <h1 className="welcome-title">AI FAQ College Chat Bot</h1>
      <p className="welcome-tagline">Ask anything about your college</p>

      <p className="welcome-subtitle">
        Get answers about courses, fees, admissions, faculty, facilities,
        exams, and other college information.
      </p>

      <button
        type="button"
        className="btn-primary welcome-start-btn"
        onClick={() => onSelectPrompt('')}
      >
        Start New Chat
      </button>
    </div>
  );
}
