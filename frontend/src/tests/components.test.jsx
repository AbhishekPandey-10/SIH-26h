import { describe, it, expect } from 'vitest';
import { LANGUAGES } from '../components/kiosk/LanguageSelector';
import { STATUS_CONFIG, VerificationBadge } from '../components/doctor/VerificationBadge';
import { KioskButton } from '../components/kiosk/KioskButton';
import { KioskCard } from '../components/kiosk/KioskCard';
import { IdentityScreen } from '../components/kiosk/IdentityScreen';
import { KioskDashboard } from '../components/kiosk/KioskDashboard';
import { IdleTimeoutOverlay } from '../components/kiosk/IdleTimeoutOverlay';
import { InterviewScreen } from '../components/interview/InterviewScreen';
import { ConsentFlow } from '../components/kiosk/ConsentFlow';

// Module B Components
import { CameraCapture } from '../components/documents/CameraCapture';
import { ScanProgress } from '../components/documents/ScanProgress';
import { BboxOverlay } from '../components/documents/BboxOverlay';
import { DocumentList } from '../components/documents/DocumentList';
import { DocumentWorkflow } from '../components/documents/DocumentWorkflow';

// Module C Components
import { SummarySection } from '../components/doctor/SummarySection';
import { AskBackPanel } from '../components/doctor/AskBackPanel';
import { ConfirmPush } from '../components/doctor/ConfirmPush';
import { SummaryView } from '../components/doctor/SummaryView';
import { DoctorDashboard } from '../pages/DoctorDashboard';

describe('Design System Constants and Configurations', () => {
  it('defines all Pan-India languages with native scripts including Punjabi, Odia, Assamese, and Urdu', () => {
    expect(LANGUAGES).toHaveLength(14);
    const codes = LANGUAGES.map((l) => l.code);
    expect(codes[0]).toBe('hi');
    expect(codes[1]).toBe('en');
    expect(codes[2]).toBe('pa');
    expect(codes).toContain('or');
    expect(codes).toContain('as');
    expect(codes).toContain('ur');
    expect(codes).toContain('ta');
    expect(codes).toContain('te');
    expect(codes).toContain('bn');
    expect(codes).toContain('mr');
    expect(codes).toContain('kn');
    expect(codes).toContain('ml');
    expect(codes).toContain('gu');
    expect(codes).toContain('more');
  });

  it('defines clinical verification badge states including doctor_edited with distinct color tokens', () => {
    expect(STATUS_CONFIG).toHaveProperty('patient_reported');
    expect(STATUS_CONFIG).toHaveProperty('document_extracted');
    expect(STATUS_CONFIG).toHaveProperty('needs_confirmation');
    expect(STATUS_CONFIG).toHaveProperty('conflicting');
    expect(STATUS_CONFIG).toHaveProperty('doctor_edited');

    expect(STATUS_CONFIG.patient_reported.color).toBe('var(--color-patient-reported)');
    expect(STATUS_CONFIG.document_extracted.color).toBe('var(--color-document-extracted)');
    expect(STATUS_CONFIG.needs_confirmation.color).toBe('var(--color-needs-confirmation)');
    expect(STATUS_CONFIG.conflicting.color).toBe('var(--color-conflicting)');
    expect(STATUS_CONFIG.doctor_edited.color).toBe('#9333EA');
  });

  it('exports all Module D Kiosk components without runtime crashes', () => {
    expect(KioskButton).toBeDefined();
    expect(KioskCard).toBeDefined();
    expect(IdentityScreen).toBeDefined();
    expect(KioskDashboard).toBeDefined();
    expect(IdleTimeoutOverlay).toBeDefined();
    expect(InterviewScreen).toBeDefined();
    expect(ConsentFlow).toBeDefined();
  });

  it('exports all Module B Document OCR & Extraction components without runtime crashes', () => {
    expect(CameraCapture).toBeDefined();
    expect(ScanProgress).toBeDefined();
    expect(BboxOverlay).toBeDefined();
    expect(DocumentList).toBeDefined();
    expect(DocumentWorkflow).toBeDefined();
  });

  it('exports all Module C Doctor UI & Scribe components without runtime crashes', () => {
    expect(VerificationBadge).toBeDefined();
    expect(SummarySection).toBeDefined();
    expect(AskBackPanel).toBeDefined();
    expect(ConfirmPush).toBeDefined();
    expect(SummaryView).toBeDefined();
    expect(DoctorDashboard).toBeDefined();
  });
});
