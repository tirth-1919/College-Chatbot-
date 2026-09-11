import React, { useState, useRef, useEffect } from 'react';
import { 
  Send, Square, Mic, Paperclip, X, FileText, Image as ImageIcon 
} from 'lucide-react';
import { apiClient } from '../services/api';

export function Composer({ onSendMessage, isStreaming, onStopStreaming }) {
  const [text, setText] = useState('');
  const [attachments, setAttachments] = useState([]);
  const [isListening, setIsListening] = useState(false);
  const [uploading, setUploading] = useState(false);
  const textareaRef = useRef(null);
  const fileInputRef = useRef(null);
  const recognitionRef = useRef(null);

  // Web Speech API Voice Recognition setup
  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
      const recognition = new SpeechRecognition();
      recognition.continuous = false;
      recognition.interimResults = true;
      recognition.lang = 'en-IN'; // Also recognizes Hinglish/Gujlish accents

      recognition.onresult = (event) => {
        const transcript = Array.from(event.results)
          .map(result => result[0].transcript)
          .join('');
        setText(prev => (prev ? `${prev} ${transcript}` : transcript));
      };

      recognition.onend = () => {
        setIsListening(false);
      };

      recognition.onerror = () => {
        setIsListening(false);
      };

      recognitionRef.current = recognition;
    }
  }, []);

  const toggleListening = () => {
    if (!recognitionRef.current) {
      alert("Voice recognition is not supported in this browser. Please use Google Chrome or Edge.");
      return;
    }
    if (isListening) {
      recognitionRef.current.stop();
      setIsListening(false);
    } else {
      recognitionRef.current.start();
      setIsListening(true);
    }
  };

  const handleTextChange = (e) => {
    setText(e.target.value);
    // Auto-grow textarea
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 160)}px`;
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleFileUpload = async (e) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    setUploading(true);
    try {
      for (const file of Array.from(files)) {
        const res = await apiClient.uploadFile(file);
        setAttachments(prev => [...prev, {
          id: res.file_id,
          name: res.filename,
          size: res.size_bytes,
          ext: res.extension
        }]);
      }
    } catch (err) {
      alert(err.message || "Failed to upload file");
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handlePaste = async (e) => {
    const items = e.clipboardData?.items;
    if (!items) return;

    for (const item of items) {
      if (item.kind === 'file') {
        const file = item.getAsFile();
        if (file) {
          setUploading(true);
          try {
            const res = await apiClient.uploadFile(file);
            setAttachments(prev => [...prev, {
              id: res.file_id,
              name: res.filename,
              size: res.size_bytes,
              ext: res.extension
            }]);
          } catch (err) {
            alert(err.message);
          } finally {
            setUploading(false);
          }
        }
      }
    }
  };

  const handleSubmit = () => {
    if ((!text.trim() && attachments.length === 0) || isStreaming) return;
    onSendMessage(text.trim(), attachments);
    setText('');
    setAttachments([]);
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  return (
    <div className="chat-composer-container">
      <div className="composer-box" onPaste={handlePaste}>
        {/* Attachment Chips */}
        {attachments.length > 0 && (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginBottom: '4px' }}>
            {attachments.map((att, idx) => (
              <div key={idx} className="attachment-chip">
                <FileText size={13} color="var(--ait-accent)" />
                <span>{att.name}</span>
                <button 
                  style={{ background: 'none', border: 'none', color: 'var(--text-dim)', cursor: 'pointer', display: 'flex' }}
                  onClick={() => setAttachments(prev => prev.filter((_, i) => i !== idx))}
                >
                  <X size={12} />
                </button>
              </div>
            ))}
          </div>
        )}

        <textarea
          ref={textareaRef}
          className="composer-textarea"
          placeholder={uploading ? "Securing and uploading document..." : "Ask AIT Assistant in English, Gujarati, Hindi (e.g. BCA fees, DBMS faculty, library photo)..."}
          value={text}
          onChange={handleTextChange}
          onKeyDown={handleKeyDown}
          rows={1}
          disabled={uploading}
        />

        <div className="composer-actions">
          <div className="composer-left-tools">
            <input 
              type="file" 
              ref={fileInputRef} 
              style={{ display: 'none' }} 
              onChange={handleFileUpload}
              multiple 
            />
            <button 
              className="composer-tool-btn" 
              onClick={() => fileInputRef.current?.click()}
              title="Attach document or image (PDF, DOCX, XLSX, PNG, JPG)"
            >
              <Paperclip size={18} />
            </button>
            <button 
              className={`composer-tool-btn ${isListening ? 'active' : ''}`}
              onClick={toggleListening}
              title={isListening ? "Listening... click to stop" : "Voice input (Web Speech)"}
            >
              <Mic size={18} />
            </button>
          </div>

          <div>
            {isStreaming ? (
              <button className="send-btn" onClick={onStopStreaming} title="Stop generation">
                <Square size={16} />
              </button>
            ) : (
              <button 
                className="send-btn" 
                onClick={handleSubmit} 
                disabled={(!text.trim() && attachments.length === 0) || uploading}
                title="Send query"
              >
                <Send size={16} />
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
