import React, { useState } from 'react';

// Anatomical region definitions with bilingual labels
export const BODY_REGIONS_FRONT = [
  { id: 'head_neck', label_en: 'Head & Neck', label_hi: 'सिर और गर्दन', path: 'M 90 35 C 90 15, 130 15, 130 35 C 130 55, 90 55, 90 35 Z M 100 55 L 100 70 L 120 70 L 120 55 Z' },
  { id: 'left_shoulder', label_en: 'Left Shoulder', label_hi: 'बायां कंधा', path: 'M 125 70 L 160 80 L 155 105 L 125 90 Z' },
  { id: 'right_shoulder', label_en: 'Right Shoulder', label_hi: 'दायां कंधा', path: 'M 95 70 L 60 80 L 65 105 L 95 90 Z' },
  { id: 'left_chest', label_en: 'Left Chest', label_hi: 'बाईं छाती (Left Chest)', path: 'M 110 80 L 135 85 L 135 125 L 110 125 Z' },
  { id: 'center_chest', label_en: 'Center Chest', label_hi: 'छाती का बीच (Center Chest)', path: 'M 100 80 L 120 80 L 120 125 L 100 125 Z' },
  { id: 'right_chest', label_en: 'Right Chest', label_hi: 'दाईं छाती (Right Chest)', path: 'M 85 85 L 110 80 L 110 125 L 85 125 Z' },
  { id: 'left_arm', label_en: 'Left Arm', label_hi: 'बायां हाथ', path: 'M 155 105 L 175 160 L 160 165 L 140 110 Z M 160 165 L 170 215 L 155 218 L 145 170 Z' },
  { id: 'right_arm', label_en: 'Right Arm', label_hi: 'दायां हाथ', path: 'M 65 105 L 45 160 L 60 165 L 80 110 Z M 60 165 L 50 215 L 65 218 L 75 170 Z' },
  { id: 'upper_abdomen', label_en: 'Upper Abdomen (Epigastrium)', label_hi: 'पेट का ऊपरी हिस्सा', path: 'M 90 127 L 130 127 L 128 155 L 92 155 Z' },
  { id: 'lower_abdomen', label_en: 'Lower Abdomen / Pelvis', label_hi: 'पेट का निचला हिस्सा / पेल्विस', path: 'M 92 157 L 128 157 L 125 185 L 95 185 Z' },
  { id: 'left_leg', label_en: 'Left Leg', label_hi: 'बायां पैर', path: 'M 112 187 L 128 187 L 125 280 L 112 280 Z M 112 282 L 125 282 L 123 370 L 110 370 Z' },
  { id: 'right_leg', label_en: 'Right Leg', label_hi: 'दायां पैर', path: 'M 92 187 L 108 187 L 108 280 L 95 280 Z M 95 282 L 108 282 L 110 370 L 97 370 Z' },
];

export const BODY_REGIONS_BACK = [
  { id: 'back_head_neck', label_en: 'Back of Head & Neck', label_hi: 'सिर का पिछला हिस्सा व गर्दन', path: 'M 90 35 C 90 15, 130 15, 130 35 C 130 55, 90 55, 90 35 Z M 100 55 L 100 70 L 120 70 L 120 55 Z' },
  { id: 'upper_back', label_en: 'Upper Back / Scapula', label_hi: 'ऊपरी पीठ (Upper Back)', path: 'M 85 80 L 135 80 L 132 135 L 88 135 Z' },
  { id: 'lower_back', label_en: 'Lower Back (Lumbar)', label_hi: 'निचली पीठ / कमर (Lower Back)', path: 'M 88 137 L 132 137 L 130 185 L 90 185 Z' },
  { id: 'back_left_arm', label_en: 'Left Arm (Posterior)', label_hi: 'बायां हाथ (पीछे)', path: 'M 135 85 L 175 160 L 160 165 L 132 105 Z M 160 165 L 170 215 L 155 218 L 145 170 Z' },
  { id: 'back_right_arm', label_en: 'Right Arm (Posterior)', label_hi: 'दायां हाथ (पीछे)', path: 'M 85 85 L 45 160 L 60 165 L 88 105 Z M 60 165 L 50 215 L 65 218 L 75 170 Z' },
  { id: 'gluteal', label_en: 'Gluteal / Hip Region', label_hi: 'नितंब / कूल्हा (Hips)', path: 'M 90 187 L 130 187 L 126 215 L 94 215 Z' },
  { id: 'back_left_leg', label_en: 'Left Leg (Posterior)', label_hi: 'बायां पैर (पीछे)', path: 'M 112 217 L 126 217 L 124 290 L 112 290 Z M 112 292 L 124 292 L 122 370 L 110 370 Z' },
  { id: 'back_right_leg', label_en: 'Right Leg (Posterior)', label_hi: 'दायां पैर (पीछे)', path: 'M 94 217 L 108 217 L 108 290 L 96 290 Z M 96 292 L 108 292 L 110 370 L 98 370 Z' },
];

export default function BodyMap({
  language = 'hi',
  initialSelected = [],
  onConfirm = () => {},
  onSkip = () => {},
}) {
  const [view, setView] = useState('front'); // 'front' | 'back'
  const [selectedRegions, setSelectedRegions] = useState(initialSelected);
  const isHi = language === 'hi';

  const currentList = view === 'front' ? BODY_REGIONS_FRONT : BODY_REGIONS_BACK;

  const toggleRegion = (region) => {
    const label = isHi ? region.label_hi : region.label_en;
    setSelectedRegions((prev) =>
      prev.includes(label)
        ? prev.filter((r) => r !== label)
        : [...prev, label]
    );
  };

  const handleSystemic = () => {
    const label = isHi ? 'पूरे शरीर में (Whole body / Systemic)' : 'Whole body / Systemic';
    setSelectedRegions([label]);
  };

  const handleClear = () => {
    setSelectedRegions([]);
  };

  const handleDone = () => {
    onConfirm(selectedRegions);
  };

  return (
    <div
      style={{
        background: '#ffffff',
        borderRadius: '16px',
        padding: '24px',
        boxShadow: '0 8px 30px rgba(0, 0, 0, 0.08)',
        maxWidth: '720px',
        margin: '0 auto',
        fontFamily: 'Inter, system-ui, sans-serif',
      }}
    >
      {/* Header */}
      <div style={{ textAlign: 'center', marginBottom: '16px' }}>
        <h2 style={{ fontSize: '22px', fontWeight: 700, color: '#1e293b', margin: '0 0 6px 0' }}>
          {isHi ? 'शरीर में दर्द का स्थान चुनें' : 'Locate Pain on the 2D Body Map'}
        </h2>
        <p style={{ fontSize: '14px', color: '#64748b', margin: 0 }}>
          {isHi
            ? 'शरीर के उस अंग पर स्पर्श करें जहाँ आपको दर्द या तकलीफ़ है।'
            : 'Tap on the body region(s) where you are experiencing pain or discomfort.'}
        </p>
      </div>

      {/* Front / Back Toggle Buttons */}
      <div style={{ display: 'flex', justifyContent: 'center', gap: '12px', marginBottom: '20px' }}>
        <button
          type="button"
          onClick={() => setView('front')}
          style={{
            padding: '10px 24px',
            borderRadius: '9999px',
            fontWeight: 600,
            fontSize: '14px',
            border: 'none',
            cursor: 'pointer',
            transition: 'all 0.2s',
            background: view === 'front' ? '#2563eb' : '#f1f5f9',
            color: view === 'front' ? '#ffffff' : '#475569',
          }}
        >
          {isHi ? 'सामने का भाग (Front)' : 'Front View'}
        </button>
        <button
          type="button"
          onClick={() => setView('back')}
          style={{
            padding: '10px 24px',
            borderRadius: '9999px',
            fontWeight: 600,
            fontSize: '14px',
            border: 'none',
            cursor: 'pointer',
            transition: 'all 0.2s',
            background: view === 'back' ? '#2563eb' : '#f1f5f9',
            color: view === 'back' ? '#ffffff' : '#475569',
          }}
        >
          {isHi ? 'पीछे का भाग (Back)' : 'Back View'}
        </button>
      </div>

      {/* 2D Interactive SVG Container */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          background: '#f8fafc',
          borderRadius: '12px',
          padding: '20px',
          border: '1px solid #e2e8f0',
        }}
      >
        <svg
          viewBox="30 10 160 380"
          style={{ width: '280px', height: '380px', filter: 'drop-shadow(0 4px 6px rgba(0,0,0,0.05))' }}
        >
          {/* Base anatomical silhouette outline */}
          <path
            d="M 110 15 C 95 15, 88 35, 95 55 L 60 80 L 45 160 L 50 215 L 65 218 L 80 160 L 88 185 L 95 370 L 110 370 L 112 210 L 115 370 L 130 370 L 135 185 L 145 160 L 160 218 L 175 215 L 175 160 L 160 80 L 125 55 C 132 35, 125 15, 110 15 Z"
            fill="#e2e8f0"
            stroke="#cbd5e1"
            strokeWidth="2"
          />

          {/* Interactive Clickable Regions */}
          {currentList.map((region) => {
            const label = isHi ? region.label_hi : region.label_en;
            const isSelected = selectedRegions.includes(label);

            return (
              <path
                key={region.id}
                d={region.path}
                onClick={() => toggleRegion(region)}
                style={{
                  cursor: 'pointer',
                  transition: 'all 0.2s ease',
                  fill: isSelected ? '#ef4444' : '#cbd5e1',
                  stroke: isSelected ? '#991b1b' : '#94a3b8',
                  strokeWidth: isSelected ? 3 : 1.5,
                  opacity: isSelected ? 0.95 : 0.65,
                }}
              >
                <title>{label}</title>
              </path>
            );
          })}
        </svg>
      </div>

      {/* Selected tags */}
      <div style={{ marginTop: '16px', minHeight: '44px' }}>
        <div style={{ fontSize: '13px', fontWeight: 600, color: '#475569', marginBottom: '6px' }}>
          {isHi ? 'चुने गए अंग (Selected Regions):' : 'Selected Anatomical Regions:'}
        </div>
        {selectedRegions.length === 0 ? (
          <span style={{ fontSize: '13px', color: '#94a3b8', fontStyle: 'italic' }}>
            {isHi ? 'कोई अंग नहीं चुना गया है (कृपया नक्शे पर स्पर्श करें)' : 'None selected (tap body parts above)'}
          </span>
        ) : (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
            {selectedRegions.map((reg) => (
              <span
                key={reg}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  background: '#fee2e2',
                  color: '#991b1b',
                  fontSize: '12px',
                  fontWeight: 600,
                  padding: '4px 10px',
                  borderRadius: '9999px',
                  border: '1px solid #fca5a5',
                }}
              >
                {reg}
                <button
                  type="button"
                  onClick={() => setSelectedRegions(selectedRegions.filter((r) => r !== reg))}
                  style={{
                    marginLeft: '6px',
                    border: 'none',
                    background: 'transparent',
                    color: '#991b1b',
                    cursor: 'pointer',
                    fontWeight: 700,
                    padding: 0,
                  }}
                >
                  ×
                </button>
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Action Buttons */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginTop: '24px',
          paddingTop: '16px',
          borderTop: '1px solid #f1f5f9',
          gap: '12px',
          flexWrap: 'wrap',
        }}
      >
        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            type="button"
            onClick={handleSystemic}
            style={{
              padding: '8px 16px',
              borderRadius: '8px',
              border: '1px solid #cbd5e1',
              background: '#f8fafc',
              fontSize: '13px',
              color: '#334155',
              fontWeight: 500,
              cursor: 'pointer',
            }}
          >
            {isHi ? 'पूरे शरीर में (Systemic)' : 'Whole Body / Systemic'}
          </button>
          <button
            type="button"
            onClick={onSkip}
            style={{
              padding: '8px 16px',
              borderRadius: '8px',
              border: '1px solid #cbd5e1',
              background: '#f8fafc',
              fontSize: '13px',
              color: '#64748b',
              fontWeight: 500,
              cursor: 'pointer',
            }}
          >
            {isHi ? 'छोड़ें (Skip)' : 'Skip / Not Localized'}
          </button>
        </div>

        <div style={{ display: 'flex', gap: '8px' }}>
          {selectedRegions.length > 0 && (
            <button
              type="button"
              onClick={handleClear}
              style={{
                padding: '10px 16px',
                borderRadius: '8px',
                border: 'none',
                background: '#f1f5f9',
                fontSize: '14px',
                color: '#475569',
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              {isHi ? 'हटाएं (Clear)' : 'Clear'}
            </button>
          )}

          <button
            type="button"
            onClick={handleDone}
            style={{
              padding: '10px 24px',
              borderRadius: '8px',
              border: 'none',
              background: '#16a34a',
              color: '#ffffff',
              fontSize: '14px',
              fontWeight: 600,
              cursor: 'pointer',
              boxShadow: '0 2px 8px rgba(22, 163, 74, 0.3)',
            }}
          >
            {isHi ? 'आगे बढ़ें (Confirm & Continue)' : 'Confirm Selection'}
          </button>
        </div>
      </div>
    </div>
  );
}
