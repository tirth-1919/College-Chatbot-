import React from 'react';
import { 
  GraduationCap, BadgeDollarSign, BookOpen, 
  UserCheck, Briefcase, Image as ImageIcon 
} from 'lucide-react';

const SUGGESTIONS = [
  { prompt: "What courses does AIT offer?", icon: GraduationCap, category: "Programs" },
  { prompt: "What are the BCA fees?", icon: BadgeDollarSign, category: "Fees" },
  { prompt: "Show me the AIT library.", icon: BookOpen, category: "Facilities" },
  { prompt: "Who teaches DBMS?", icon: UserCheck, category: "Faculty" },
  { prompt: "Tell me about AIT placements.", icon: Briefcase, category: "Placements" },
  { prompt: "Show AIT campus photos.", icon: ImageIcon, category: "Campus Media" }
];

export function WelcomeHero({ onSelectPrompt }) {
  return (
    <div className="welcome-hero">
      <div className="welcome-logo-wrap">
        <img src="/ait-logo.webp" alt="AIT Official Logo" className="welcome-logo" />
      </div>

      <h1 className="welcome-title">Ahmedabad Institute of Technology</h1>
      <p className="welcome-subtitle">
        Official AI Assistant grounded in verified institutional data from 
        <a href="https://www.aitindia.in" target="_blank" rel="noreferrer" style={{ color: 'var(--ait-accent)', textDecoration: 'none', marginLeft: '4px' }}>
          aitindia.in
        </a>. Ask about courses, fees, syllabus, faculty, admissions, or view verified campus photos.
      </p>

      <div className="suggestions-grid">
        {SUGGESTIONS.map((item, idx) => {
          const IconComp = item.icon;
          return (
            <div 
              key={idx} 
              className="suggestion-card" 
              onClick={() => onSelectPrompt(item.prompt)}
            >
              <div className="suggestion-icon">
                <IconComp size={20} />
              </div>
              <div className="suggestion-text">
                {item.prompt}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
