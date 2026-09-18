import React from 'react';
import KioskCard from './KioskCard';

/**
 * LanguageSelector — Full-screen high-contrast touch grid for Indian OPD kiosks.
 * Displays 9 major Indian languages in their native script and English.
 */
export const LANGUAGES = [
  { code: 'hi', native: 'हिन्दी', english: 'Hindi', script: 'नमस्ते' },
  { code: 'en', native: 'English', english: 'English', script: 'Welcome' },
  { code: 'ta', native: 'தமிழ்', english: 'Tamil', script: 'வணக்கம்' },
  { code: 'te', native: 'తెలుగు', english: 'Telugu', script: 'నమస్కారం' },
  { code: 'bn', native: 'বাংলা', english: 'Bengali', script: 'নমস্কার' },
  { code: 'mr', native: 'मराठी', english: 'Marathi', script: 'नमस्कार' },
  { code: 'kn', native: 'ಕನ್ನಡ', english: 'Kannada', script: 'ನಮಸ್ಕಾರ' },
  { code: 'ml', native: 'മലയാളം', english: 'Malayalam', script: 'നമസ്കാരം' },
  { code: 'gu', native: 'ગુજરાતી', english: 'Gujarati', script: 'નમસ્તે' },
];

export const LanguageSelector = ({
  selectedLanguage = 'hi',
  onSelectLanguage,
  className = '',
}) => {
  return (
    <div style={{
      width: '100%',
      maxWidth: '1080px',
      margin: '0 auto',
      padding: '32px 20px',
      display: 'flex',
      flexDirection: 'column',
      gap: '32px',
    }} className={className}>
      <div style={{ textAlign: 'center' }}>
        <h1 style={{
          fontSize: '32px',
          fontWeight: 800,
          color: 'var(--color-text-primary)',
          marginBottom: '8px',
          letterSpacing: '-0.02em',
        }}>
          अपनी भाषा चुनें / Select Your Language
        </h1>
        <p style={{
          fontSize: '18px',
          color: 'var(--color-text-secondary)',
        }}>
          डॉक्टर से मिलने से पहले कृपया अपनी पसंदीदा भाषा का चयन करें
        </p>
      </div>

      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
        gap: '20px',
      }}>
        {LANGUAGES.map((lang) => {
          const isSelected = selectedLanguage === lang.code;
          return (
            <KioskCard
              key={lang.code}
              selected={isSelected}
              onClick={() => onSelectLanguage && onSelectLanguage(lang.code)}
              padding="24px"
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                minHeight: '100px',
              }}
            >
              <div>
                <div style={{
                  fontSize: '28px',
                  fontWeight: 700,
                  color: isSelected ? '#FFFFFF' : 'var(--color-text-primary)',
                  fontFamily: "'Noto Sans Devanagari', sans-serif",
                }}>
                  {lang.native}
                </div>
                <div style={{
                  fontSize: '16px',
                  color: isSelected ? 'var(--color-blue-info)' : 'var(--color-text-secondary)',
                  fontWeight: 500,
                  marginTop: '4px',
                }}>
                  {lang.english}
                </div>
              </div>

              <div style={{
                fontSize: '18px',
                color: 'var(--color-text-muted)',
                fontStyle: 'italic',
                padding: '6px 12px',
                borderRadius: '8px',
                background: 'rgba(255, 255, 255, 0.04)',
              }}>
                {lang.script}
              </div>
            </KioskCard>
          );
        })}
      </div>
    </div>
  );
};

export default LanguageSelector;
