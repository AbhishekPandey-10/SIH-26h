import { describe, it, expect } from 'vitest';
import { LANGUAGES } from '../components/kiosk/LanguageSelector';
import { STATUS_CONFIG } from '../components/doctor/VerificationBadge';

describe('Design System Constants and Configurations', () => {
  it('defines all 9 Indian languages with native scripts', () => {
    expect(LANGUAGES).toHaveLength(9);
    const codes = LANGUAGES.map((l) => l.code);
    expect(codes).toContain('hi');
    expect(codes).toContain('en');
    expect(codes).toContain('ta');
    expect(codes).toContain('te');
    expect(codes).toContain('bn');
    expect(codes).toContain('mr');
    expect(codes).toContain('kn');
    expect(codes).toContain('ml');
    expect(codes).toContain('gu');
  });

  it('defines 4 clinical verification badge states with distinct color tokens', () => {
    expect(STATUS_CONFIG).toHaveProperty('patient_reported');
    expect(STATUS_CONFIG).toHaveProperty('document_extracted');
    expect(STATUS_CONFIG).toHaveProperty('needs_confirmation');
    expect(STATUS_CONFIG).toHaveProperty('conflicting');

    expect(STATUS_CONFIG.patient_reported.color).toBe('var(--color-patient-reported)');
    expect(STATUS_CONFIG.document_extracted.color).toBe('var(--color-document-extracted)');
    expect(STATUS_CONFIG.needs_confirmation.color).toBe('var(--color-needs-confirmation)');
    expect(STATUS_CONFIG.conflicting.color).toBe('var(--color-conflicting)');
  });
});
