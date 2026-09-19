# MediKiosk pre-launch repair: agent prompt pack

This pack contains **nine agent assignments**, not nine independent rewrites. Give every agent the common instructions below, followed by its numbered assignment. If agents can read this repository, use the launcher prompts below: each directs the agent to read its full assignment here.

The objective is to repair the audited system, not merely make existing tests pass. Do not use live patient data or transmit records to external systems while validating repairs.

## Launcher prompts

1. **Database/contracts:** Read `docs/AGENT_FIX_PROMPTS.md`, including Common instructions and Assignment 1. Implement Assignment 1 completely and provide its handoff. Do not implement other assignments.
2. **Access/consent/privacy:** Read `docs/AGENT_FIX_PROMPTS.md`, including Common instructions and Assignment 2. Check Assignment 1's handoff, then implement Assignment 2 completely.
3. **Interview/emergency safety:** Read `docs/AGENT_FIX_PROMPTS.md`, including Common instructions and Assignment 3. Check the database, contract, and authorization handoffs, then implement Assignment 3 completely.
4. **Documents/OCR/labs:** Read `docs/AGENT_FIX_PROMPTS.md`, including Common instructions and Assignment 4. Check the database, contract, and authorization handoffs, then implement Assignment 4 completely.
5. **Clinical summaries/medication intelligence:** Read `docs/AGENT_FIX_PROMPTS.md`, including Common instructions and Assignment 5. Check Assignments 1–4's relevant handoffs, then implement Assignment 5 completely.
6. **FHIR/export:** Read `docs/AGENT_FIX_PROMPTS.md`, including Common instructions and Assignment 6. Check the consent, summary-version, and contract handoffs, then implement Assignment 6 completely.
7. **Kiosk frontend:** Read `docs/AGENT_FIX_PROMPTS.md`, including Common instructions and Assignment 7. Check backend contract handoffs, then implement Assignment 7 completely.
8. **Doctor/staff frontend/design system:** Read `docs/AGENT_FIX_PROMPTS.md`, including Common instructions and Assignment 8. Check backend and kiosk frontend handoffs, then implement Assignment 8 completely.
9. **Adversarial integration/evaluation:** Read `docs/AGENT_FIX_PROMPTS.md`, including Common instructions and Assignment 9. Review every handoff, reproduce and fix remaining integration defects, and produce the final evidence-based launch assessment.

## Execution order and ownership

Safest sequence: **1 → 2 → 3 and 4 → 5 → 6 → 7 and 8 → 9**. Run 3/4 or 7/8 concurrently only in separate worktrees or with explicit file ownership. This document does not authorize an agent to spawn additional agents; use the orchestration capabilities and permissions supplied by the user.

Assignment 1 establishes baseline schema/contracts. After its handoff, a producer may extend the contract for its own domain, but must update Pydantic, TypeScript, documentation, and consumers together. Simultaneous edits to shared schema files require serialization or separate branches. Later agents must not overwrite earlier agents' corrections.

Assignment 2 owns central access/lifecycle policy. Domain agents own integrating that policy into their routes and services. Assignment 9 verifies no route or background path was missed. An authentication helper existing in a file is not evidence that requests are protected.

Each assignment owns its meaningful regression tests. Assignment 9 adds adversarial end-to-end coverage and evaluation infrastructure; it is not a substitute for testing earlier work.

Suggested handoffs: `docs/repair-handoffs/01-database-contracts.md` through `08-clinician-ui.md`. Keep handoffs free of credentials and patient information. Include changed interfaces, migrations, environment settings, tests run, limitations, and exact remaining dependencies.

## Common instructions — include with every assignment

```text
ROLE
You are a staff-level engineer repairing MediKiosk, PS ID26047, following an adversarial pre-launch audit. Treat patient safety, evidence integrity, privacy, and correct state transitions as more important than a polished demo or a green test count.

BASELINE AND EVIDENCE
The audit examined revision b3d619e. Re-read current files and applicable AGENTS.md instructions before editing; line numbers may have moved and other repairs may already be present. Preserve unrelated user changes. The audit made no application source changes.

The canonical public-schema entry point is shared/schemas/__init__.py; it currently re-exports backend/app/shared/schemas.py. Frontend declarations are in frontend/src/types/schemas.ts. Design tokens are in frontend/src/styles/tokens.css. Determine whether other similarly named files are shims, unused duplicates, or active consumers; do not invent another source of truth.

Verified audit reproductions included:
- Fresh Alembic head differs from ORM metadata: missing session/transcript/summary fields, missing summary_resolutions, and nullable extracted_entities.created_at.
- Bulk SQL changed a consent grant despite ORM append-only callbacks.
- PUT summary field returned edited text, but GET returned the original stored content.
- A nonexistent document citation acquired a sample crop, confidence 0.92, and document_extracted status.
- Empty contradiction inputs produced an invented Amlodipine-started event.
- HbA1c: 7.1% was parsed as 1 and marked normal; Platelets 1.8 Lakhs /cumm was compared as 1.8.
- With Gemini disabled, 109 configured keyword phrases matched scan_text but were discarded by confirmation. This is a count of configured phrases, not a measured clinical sensitivity rate.
- REST emergency input returned a hold but persisted zero red-flag events.
- A real interview start with seeded medication evidence loaded empty recall context.
- An unscoped citation lookup returned another session's transcript.
- Export reached a stubbed transport without any consent record; no real external export was performed.
- Session end left persisted entities untouched regardless of consent.

Seven existing benchmark tests pass offline after output-encoding handling, with 95.6% complaint-category agreement, 98.1% assumed section coverage, 0/50 keyword false positives, and 100% annotation self-consistency. These do NOT establish clinical triage, elicitation, confirmation, or OCR accuracy. Eight frontend tests pass largely by checking exports/constants rather than mounted behavior. Browser/DevTools inspection and PostgreSQL execution were not performed in the original audit. Do not represent those as completed checks.

METHOD
1. Trace the actual application path and every consumer before changing a contract or shared assumption. Search exact string comparisons, duplicate implementations, background jobs, demo scripts, tests, and deployment configuration.
2. Write a short implementation plan and inventory affected interfaces. Do not stop at the plan: implement the authorized assignment and verify it.
3. Fix root causes. Remove runtime fabrication, transport-specific safety logic, unvalidated dictionaries, silent success, and identity ambiguity. Do not hide failures by catching Exception and returning success, sample content, or empty clinical results.
4. Preserve uncertainty. Missing evidence is not a normal result, no allergy, no medication, no emergency, or verified identity. A failed check is not a clean check.
5. Put demo fixtures behind an explicit isolated demo deployment/provider. Do not use network failures, empty data, missing files, or non-2xx responses as permission to create sample patient facts.
6. Keep clinical evidence immutable and patient-scoped. Preserve provenance, distinctions between current and historical medications, and clinician review history. Do not infer medical truth from a display badge or model confidence alone.
7. Do not implement clinical decision thresholds or drug interactions by guessing. Preserve clearly specified behavior, use the repository's intended data sources, and explicitly surface clinically unresolved policy instead of inventing it.
8. Match request, response, event, enum, and TypeScript definitions. Validate at server boundaries and handle all outcomes at frontend boundaries. If a response shape changes, repair every caller and its tests.
9. Use isolated disposable databases and synthetic fixtures. Prevent tests from reading production .env credentials, touching existing medikiosk_dev.db files, or making external clinical/model/export calls. Inject transports/providers. Live external verification requires appropriate existing authorization; do not create it implicitly.
10. Run behavior-focused regressions plus relevant existing tests. Verify writes using a fresh DB session. Test negative paths, exact boundaries, concurrency, and retries where relevant. Do not weaken assertions to bless broken behavior.
11. Avoid broad unrelated rewrites or dependency upgrades. Refactor when it removes a demonstrated structural defect. Keep each repair reviewable.
12. Continue through routine implementation choices without repeatedly asking permission. For a clinical/legal/product policy that cannot safely be inferred, implement an explicit unavailable/blocked state, document the unresolved decision, and continue independent work. Do not silently assert compliance.

DEFINITION OF DONE
- The identified root causes and reused instances in your assigned scope are repaired.
- APIs and UI never claim completion when persistence, delivery, verification, or consent checks failed.
- Meaningful regression tests fail against the previous defective behavior and pass against the repair.
- Contract/schema changes and required operational steps are documented.
- No fabricated evidence or uncontrolled outbound requests are introduced.
- Handoff lists changed files, exact tests/results, evidence limitations, and remaining cross-assignment dependencies.

FINAL HANDOFF FORMAT
Implemented: concise list of outcomes and root causes removed.
Interfaces/migrations: exact changes other agents must consume.
Validation: commands, results, negative/concurrency cases exercised.
Remaining: explicit unresolved dependencies or unavailable verification; no optimistic checkmarks.
```

## Assignment 1 — Database integrity and canonical contracts

### Copyable task

```text
Implement the database/schema foundation and public-contract baseline. Read Common instructions first.

PRIMARY OWNERSHIP
- backend/app/db/models.py and backend/app/db/database.py
- backend/migrations/env.py and backend/migrations/versions/
- shared/schemas/__init__.py, backend/app/shared/schemas.py, frontend/src/types/schemas.ts
- Any actual schema compatibility shims in backend/shared/ and backend/app/shared/
- Focused database, migration, and schema tests

AUDIT CONTEXT
The fresh migration chain lacks sessions.caregiver_name/caregiver_relationship/caregiver_phone/voice_only_mode/body_map_selections/interview_mode/prakriti_result; interview_transcripts.is_proxy/proxy_name/proxy_relationship; summaries.lens/ayush_json; and summary_resolutions. extracted_entities.created_at is nullable in migrations but non-null in ORM. Also inspect leftover consent_audit.patient_id, transcript language widths, defaults, indexes, and uniqueness rather than assuming this list is exhaustive.

database.init_db uses create_all followed by unconditional ALTER TABLE statements and silently catches every exception. This masks migration drift; failed DDL also aborts a PostgreSQL transaction. Startup currently logs initialization failure and continues to report healthy.

002_consent_audit_v2 adds action with share_doctor as the default and drops consent_type. It destroys the purpose of historical consent entries. Mapper before_update/before_delete callbacks do not stop bulk SQL. Most clinical child session/document IDs have no FKs; SQLite FK enforcement is absent. Consent's FK has different behavior from the unconstrained clinical tables.

The six named shared shapes are not all executable contracts. InterviewAnswer is bypassed by transport dictionaries. ExtractedEntity uses entity_id/type/source_document_id, but routes emit id/entity_type/document_id. The canonical vital enum differs from OCR vital_sign; low-confidence state is incorrectly suffixed onto entity type. Summary sections are arbitrary strings; TypeScript omits document/conflict metadata. RedFlagEvent event_id differs from the list response's id. FHIRBundlePayload exists but export uses another shape.

IMPLEMENTATION GUIDE
1. Reconstruct the complete Alembic graph. Upgrade an empty disposable database to head and compare it against ORM metadata; also exercise representative historical schemas with existing rows. Do not use create_all to make migration tests pass.
2. Add forward reconciliation migrations with explicit backfills, nullability, defaults, FKs, indexes, and stable constraint names. Do not casually rewrite applied migrations. For the destructive consent migration, provide a safe strategy for not-yet-upgraded databases and clearly state what requires backup recovery in already-upgraded databases. Never infer lost consent purposes or grant permission by default.
3. Preserve nullable extracted document dates. Separate unknown dates from malformed source text. Backfill fields that truly must be NOT NULL without pretending invented clinical values are real.
4. Enforce consent append-only behavior at the database boundary, including direct SQL UPDATE/DELETE and bulk ORM operations. Use appropriate database roles/triggers for supported engines and controlled migration privileges. Migration history must not be an unrestricted production bypass.
5. Define FK/retention semantics with Assignment 2. Do not blanket-cascade consented medical records when deleting a transient session. Prefer explicit archival/retention ownership and a preserved minimal audit anchor. Add orphan-prevention constraints without deleting existing records silently.
6. Replace startup schema patching with migration-version/schema readiness verification. Supply explicit fresh-install and upgrade commands. Hand off the necessary app readiness changes to Assignment 2.
7. Establish public models/enums for entities, source citations, summary sections, verification, document processing status, interview answers, and red-flag lifecycle/events. Give source citations immutable evidence IDs and patient/encounter scoping. Keep confidence and verification separate from clinical entity type.
8. Define an unambiguous WebSocket envelope distinguishing question, pause, resume, acknowledgement, clarification, completion, and error events. Define separate FHIR preview/export DTOs rather than pretending a raw FHIR bundle and FHIRBundlePayload are identical. Coordinate final workflow-specific fields with the domain owners.
9. Generate TypeScript from the canonical model if practical with current tooling; otherwise add exhaustive contract-parity validation and a documented generation/update workflow. Merely widening types to any/string is not a fix.

ACCEPTANCE TESTS
- Empty database upgraded only through Alembic matches intended ORM columns, nullability, constraints, indexes, and defaults.
- Upgrade from each relevant branch/legacy schema preserves clinical records and consent meanings; unrepairable historical ambiguity is identified rather than fabricated.
- Direct SQL and bulk ORM UPDATE/DELETE against consent are rejected under application privileges.
- Invalid foreign references are rejected on every supported DB; approved retention semantics preserve consented/audit data.
- SQLite foreign_keys is enabled for application and test connections.
- Core schema examples round-trip and reject bad enums/ranges; TypeScript and API models have the same required fields and nullable semantics.
- Database initialization failure cannot be masked as successful schema readiness.

HANDOFF
Document the schema head, migration steps, recovery limitations, canonical DTOs/enums, and constraints domain agents must respect. Coordinate all later model/schema edits rather than allowing each agent to create private competing definitions.
```

## Assignment 2 — Authentication, consent, identity, and privacy lifecycle

### Copyable task

```text
Implement central access-control and encounter-lifecycle policy. Read Common instructions and Assignment 1's handoff.

PRIMARY OWNERSHIP
- backend/app/dependencies.py, app/main.py, app/config.py
- backend/app/routes/session.py and consent.py
- backend/app/services/session_manager.py and services/abdm.py
- Deployment/configuration documentation relevant to identity, readiness, and retention
- Focused authorization, consent, identity, and privacy tests
Domain owners integrate your dependencies/hooks in their own route files; coordinate these changes explicitly.

AUDIT CONTEXT
Clinical routes and sockets lack authenticated role/resource checks. Staff IDs are supplied by callers. Three taps on the kiosk logo reveal staff UI, which is not security. Backend OTP accepts 123456 without a prior transaction; ABHA identity uses a mock provider. SessionContext returns invented verified profiles after HTTP errors or network failure. Session creation/consent recording can fail while the kiosk creates a local OPD identifier and continues without durable consent.

Session end marks completed and clears only _IN_MEMORY_SESSION_CACHE plus interview_engine.sessions. It ignores consent when retaining transcripts, summaries, entities, uploaded files, queued FHIR bundles, crop bytes, contradiction actions, and other caches. Existing sockets can continue traffic and recreate state after end. There is no explicit distinction between transient session cleanup and durable consented clinical retention. Existing init_db failures are swallowed while /health returns healthy.

IMPLEMENTATION GUIDE
1. Inventory every HTTP route, WebSocket, file/crop endpoint, background mutation, diagnostic endpoint, and identity path. Produce a required-role/resource-scope matrix. Use an appropriate local authentication mechanism and explicit provider abstraction; do not invent real ABDM integration credentials.
2. Authenticate kiosk and clinician/staff identities. Authorize every resource access against encounter/patient ownership and allowed purpose. Bind staff audit identity to authentication, not request JSON. Authenticate sockets at connection and check session state on commands.
3. Remove demo OTP/profile behavior from production providers. OTP must be bound to the requested identity and transaction, expire, have attempt/replay controls, and be consumed appropriately. An unavailable verification provider must return unavailable/unverified, not verified sample demographics.
4. Derive latest effective consent by action in append-only history, including refusal/revocation. Do not interpret any historical grant as perpetual permission. Define explicit operations for share_doctor and store_abdm; consent is distinct from authentication and clinician sign-off.
5. Make session creation plus required initial consent durable and observable. If anonymous/manual intake is supported, represent it explicitly and never bind it to a sample ABHA account. Supply frontend contracts for partial failure and safe retry; no fabricated IDs masquerading as persisted sessions.
6. Implement an idempotent encounter-end workflow: atomically mark ended/invalidate new mutations, close/invalidate live transports, stop background jobs as appropriate, and apply consent-aware retention/deletion. Preserve consented records and immutable audit anchors. Purge unconsented data and associated files/caches according to explicit policy. Separate transient cleanup from clinical-record destruction.
7. Expose lifecycle registration hooks so interview, scan, crop, export, and intelligence services participate in cleanup. Include process-memory data and bounded pending work. Make partial cleanup failure observable and retryable; do not report wiped if required work failed.
8. Enforce effective consent again when queued exports are actually delivered. Ended sessions must reject stale interview/upload/clarification writes according to the explicit lifecycle contract.
9. Add readiness that checks database/schema compatibility and required operational dependencies without exposing credentials. Distinguish readiness from process liveness. Make production startup refuse demo providers and insecure defaults.

ACCEPTANCE TESTS
- Unauthenticated callers cannot read another patient's evidence, edit summaries, dismiss alerts, view staff streams, or export.
- Wrong patient/encounter access is denied even with a valid account and guessed IDs.
- Invalid, expired, replayed, wrong-identity, and unknown-transaction OTPs fail; network errors never yield verified profiles.
- Consent refusals/revocations change authorization; ordering handles repeated decisions deterministically.
- End is idempotent; consented records/audit entries survive, unconsented artifacts are removed, and socket/background traffic cannot resurrect the session.
- Privacy failure produces a truthful incomplete/error state and bounded retry.
- Database initialization/schema failure causes readiness failure and cannot appear healthy.

HANDOFF
Provide dependencies, permission matrix, consent lookup API, lifecycle hooks, error schemas, identity provider configuration, and frontend teardown requirements. List every domain route owner required to integrate these checks. Do not declare universal protection until those integrations are tested.
```

## Assignment 3 — Interview state machine, emergency safety, and clarification delivery

### Copyable task

```text
Repair the complete patient-answer → safety assessment → persistent hold → staff alert → acknowledgement/dismissal → resume path. Read Common instructions and foundational handoffs.

PRIMARY OWNERSHIP
- backend/app/routes/interview.py, red_flag.py, and patient.py's unvoiced-concern ingestion
- backend/app/services/interview_engine.py, red_flag_detector.py, question_generator.py, smart_recall.py, gemini_retry.py
- Red-flag/interview/recall/clarification regression tests
Coordinate summary updates with Assignment 5 and DB/event schemas with Assignment 1.

AUDIT CONTEXT
scan_text returns the first matching rule, despite promising highest severity. A bad rules file can produce an empty detector. Confirmation's narrow fallback suppresses configured emergencies; valid JSON with missing fields defaults negative, and bool('false') is true. Bare answers such as Yes to a self-harm question have no keyword context. Ask-back and unvoiced concerns bypass the safety flow.

The WebSocket sends the kiosk pause before persisting/broadcasting. Disconnect at that point loses the event. REST detection returns a hold without persisting or notifying staff. Two modules register the same staff socket and dismiss/ack routes with different behavior. Dismissal clears the pause without checking other unresolved alerts. Staff streams have no durable replay.

InterviewAnswer validation and question IDs are bypassed; a payload can replace the session ID. Reconnection restarts chief complaint, managers can remove a replacement socket when an old socket disconnects, and ended sessions can recreate state. Synchronous Gemini calls/time.sleep block async handlers.

Neither start transport loads real Smart Recall context. Two adapters disagree on type/entity_type, metadata keys, and exactly 0.8. Ask-back fabricates a default patient confirmation before a patient has answered.

IMPLEMENTATION GUIDE
1. Create one application-level submit-answer operation used by REST/WebSocket and analogous patient-input channels. Validate canonical answer identity, expected question/version, language, session authorization/state, idempotency, and duplicate submission behavior.
2. Make safety evaluation contextual: use the actual question and answer, evaluate all matching rules, and select/aggregate severity deterministically. Acknowledging self-harm or another contextual danger must not require the answer to repeat the question's emergency keywords. Keep false-positive handling auditable.
3. Use a strict typed confirmation result. Failure, malformed data, missing fields, or uncertain output must preserve the rule candidate/hold rather than silently clear it. Fail startup/readiness or expose a degraded safety state for invalid rule configuration; never run with an accidentally empty safety rule set.
4. Persist the alert and hold before best-effort client delivery. Use a transactional outbox or equivalent durable dispatch. Track delivery/acknowledgement separately. Notify/replay active alerts on staff connection; failed delivery must remain actionable.
5. Consolidate duplicate routers/managers. Define idempotent acknowledgement and dismissal with authenticated staff identity, reason, audit history, and lifecycle guards. Dismissing one alert must not release other active holds; acknowledgement must not imply clinical resolution.
6. Serialize encounter state transitions or use optimistic concurrency so parallel answers, reconnects, dismissals, and in-flight inference cannot advance a held/ended encounter. Recheck state/version before publishing a generated question. Restore the current question and safety state on reconnect instead of restarting intake.
7. Bind socket identity to one session. Remove a connection only if it is the exact registered connection. Clean managers in finally blocks and participate in Assignment 2's teardown. Persist/recover the state necessary to survive restart; document multi-worker behavior.
8. Wire patient-history loading into real start/resume and defined document-refresh points. Normalize a single recall evidence shape. Apply <0.5 = ordinary question, 0.5 through 0.8 inclusive = verification, >0.8 = confirmation consistently for relevant entity categories. Do not select a stale record solely because confidence is higher. Confirmed facts must refer to real evidence IDs.
9. Replace fabricated ask-back completion with a durable pending request and correlated actual reply. A disconnected patient yields pending/unavailable, not a synthetic negative finding. Route replies through safety evaluation, persist the real turn, and invoke Assignment 5's targeted summary revision API.
10. Use truly asynchronous model invocation or bounded worker execution with timeouts and cancellation. Validation belongs inside the controlled call boundary. Keep emergency persistence/acknowledgement independent of slow inference; do not retry invalid schema as if it were valid content.

ACCEPTANCE TESTS
- REST and WebSocket produce equivalent persisted safety transitions, staff events, and patient-facing state.
- Simulated socket failure on the first outgoing pause still leaves a durable alert and staff delivery job.
- Staff disconnected during detection receives unresolved alert after reconnect/restart; duplicate deliveries are safe.
- Malformed JSON, missing fields, string booleans, timeout, and unconfigured model cannot erase matched emergency candidates.
- Test configured language variants and contextual Yes to a safety question; measure false negatives as well as false positives.
- Multiple active alerts, repeated dismissal/acknowledgement, and wrong-role actions have correct results.
- Concurrent answer/inference/dismiss/end cannot publish an invalid next question or lose a hold.
- A second socket survives cleanup of the old one; ended-session messages are rejected.
- Actual API start with historical/current evidence yields recall prompts at 0.4999, 0.5, 0.8, and 0.8001; metadata/citations survive the round trip.
- Ask-back without a reply creates no invented transcript or completed field; an actual reply updates the correct request/field.
- Unvoiced concerns receive the same safety handling as ordinary answers.

HANDOFF
Document exact socket/REST event examples, pending/hold/completion semantics, recovery behavior, recall context refresh, and targeted clarification completion interface for frontend and summary agents.
```

## Assignment 4 — Document ingestion, OCR evidence, lab values, and dates

### Copyable task

```text
Repair the complete document pipeline and evidence-serving paths. Read Common instructions and database/access/safety handoffs.

PRIMARY OWNERSHIP
- backend/app/routes/documents.py and document-processing portions of routes/abdm.py
- backend/app/services/document_processor.py, crop_service.py, lab_flagging.py
- Lab parsing portions of visualization_service.py and patient.py where the same assumption is reused; coordinate patient.py edits with Assignment 3
- Document, crop, lab, and date regression tests

AUDIT CONTEXT
Empty/failed Gemini OCR unconditionally returns sample diagnoses, medications, or labs at high confidence. Empty entities endpoints return sample prescriptions; unknown/missing file requests can serve a test image, and crop_service creates a blank image for a missing original. ABDM fetch inserts hardcoded sample records for arbitrary supplied ABHA IDs.

OCR bypasses ExtractedEntity validation, accepts confidence/bbox errors, fabricates default coordinates, emits vital_sign rather than vital, and mutates entity types into medication:needs_confirmation. Downstream exact filters then omit uncertain medication evidence. Reprocessing appends new entity IDs without a defined replacement/idempotency policy. A partial processing exception can commit partial pending entities alongside error status.

Lab parsing selects the first number anywhere in the full text. HbA1c: 7.1% becomes 1; platelet Lakhs multipliers are ignored; comparators and demographic applicability are not represented. Missing units can be treated as normal/abnormal rather than unverified. normalize_indian_date formats invalid dates and passes invalid ISO strings unchanged.

Uploads use client-supplied session_id in a filesystem path without resolving session ownership/containment. Scan progress depends on transient socket messages without a reliable status recovery endpoint.

IMPLEMENTATION GUIDE
1. Require authorized active sessions and enforce configured file type/size limits. Resolve paths against the upload root and reject traversal/absolute escapes. Keep user identifiers out of path construction unless validated. Apply appropriate image/PDF support explicitly; do not pretend unsupported input was processed.
2. Separate OCR outcomes: success with entities, successful empty result, unavailable provider, invalid response, failed extraction. Remove every sample fallback from real paths. Real ABDM fetch must use an authorized configured provider; otherwise return unavailable. Demo records must live in an isolated demo provider.
3. Validate each extracted item through canonical models: entity type, nullable generic/date, finite confidence in [0,1], supported value shape, bbox length/ranges/extent, and provenance. Unknown coordinates remain unknown. Preserve raw extraction for audit where authorized without making it verified evidence.
4. Keep entity category separate from confidence/verification. Preserve low-confidence medication/allergy evidence for explicit review rather than excluding it by renamed type.
5. Make processing transactional and idempotent. Define extraction revisions and atomic publication or safe replacement; retrying the same job cannot double clinical evidence. On failure roll back partial clinical writes, then persist an explicit failed job state in a valid transaction.
6. Use a shared structured lab quantity parser with separate test identifier, numeric value, comparator, unit, multiplier, source text, and parse status. Remove test-name digits before numeric interpretation by separating fields, not by adding a special case only for HbA1c. Normalize supported units/multipliers and return cannot-verify on ambiguity/mismatch/missing required information. Map patient demographics explicitly; do not assume every patient is an adult male.
7. Reuse that parser in OCR, lab explanation, trends/sparklines, and other numeric consumers. Preserve clinical meaning of < and > rather than stripping them and claiming an exact normal result. Do not invent reference ranges or clinical conversion constants.
8. Parse dates with calendar validation under explicit day-first rules. Keep source text, nullable normalized date, and ambiguity/invalid status as appropriate. Treat document dates as dates, timestamps as timezone-aware instants; verify display/serialization around UTC and Asia/Kolkata boundaries.
9. Serve only the requested authorized real document/crop. Missing originals return a truthful error, not test/blank evidence. Validate bbox consistently for all query forms. Scope caches by record/session retention policy and purge through lifecycle hooks.
10. Persist job status/progress and expose recovery so reconnecting scan clients can reconcile without relying on missed WebSocket events. Clean sockets on all exits and prevent completed-session tasks from recreating discarded transient data.

ACCEPTANCE TESTS
- Empty, unreadable, failed, and malformed extraction produces zero invented facts and a truthful status.
- Confidence/type/bbox violations are rejected or explicitly quarantined; low-confidence evidence remains reviewable under the proper category.
- Mid-batch malformed items do not publish a partial successful extraction; reprocessing/retries do not duplicate entities.
- HbA1c full-label input, platelet Lakhs, signed/decimal/comparator values, missing/mismatched units, and applicable demographic ranges behave correctly or return unverified.
- Invalid leap days/months/dates are rejected; DD/MM dates normalize correctly; date-only values do not shift across timezones.
- Missing/unauthorized source images/crops never return fixtures; malicious session/path input cannot escape upload storage.
- Reconnected scan status matches persisted processing state, including empty success and errors.
- Privacy teardown purges authorized-to-delete source files and crop caches without deleting consented records.

HANDOFF
Provide canonical entity/job/status examples, lab parser API, missing-source semantics, provider configuration, extraction revision policy, and scan recovery endpoints for summary/frontend agents.
```

## Assignment 5 — Summaries, citations, doctor review, contradictions, and medication intelligence

### Copyable task

```text
Repair clinical synthesis and the evidence/review model. Read Common instructions and Assignments 1–4's relevant handoffs.

PRIMARY OWNERSHIP
- backend/app/services/summary_generator.py and contradiction_detector.py
- backend/app/services/polypharmacy_detector.py and polypharmacy.py
- backend/app/routes/summary.py, intelligence.py, contradictions.py if active
- Clinical portions of patient_summary.py and visualization_service.py consuming these results
- Summary/review/citation/medication intelligence regression tests
Coordinate transcript lookup implementation in interview.py with Assignment 3; define any new persisted review/evidence structures with Assignment 1.

AUDIT CONTEXT
Summary generation seeds sample prescription entities if none exist. Contradiction fallback injects sample history and unconditionally invents Amlodipine, Metformin dose changes, Glimepiride discontinuation, and lab changes. format_delta_summary fabricates changes even when there are none.

Citation validation accepts arbitrary transcript refs when the transcript set is empty and fabricates document_id/bbox/crop/confidence for nonexistent document refs. Unknown source types or source-less clinical statements evade a meaningful downgrade. Some post-validation fields introduce further nonexistent refs. Citation lookup uses reusable question IDs, can cross patient boundaries, and substitutes mock evidence.

Both doctor edit/resolve endpoints mutate dictionaries in an existing SQLAlchemy JSON list before assigning an equal list. PUT returns after, but GET persists before. A single edit sets the whole summary doctor_verified. Dashboard mount/lens switch/ask-back regenerates and replaces the same row, losing review while potentially retaining verified status. Concurrent regeneration lacks a coherent uniqueness/version policy.

Fallback synthesis retains only the first relevant HPI turn and first three document medications; conflict handling can discard the remaining medication list. Generated family_hx/personal_hx and Ayurvedic sections do not match frontend section enums.

Polypharmacy adds an entity's generic name and display value as two therapies, producing a false duplicate. First-match normalization loses other molecules in an answer or combination drug; substring 'no' removes drugs such as atenolol. Two implementations use different assumptions. Historical/current/negated therapy is not represented consistently. Contradictions use only current-session entities and .get('generic', '').lower() crashes on explicit None. Random contradiction IDs and in-memory action storage discard review decisions on refresh/restart.

IMPLEMENTATION GUIDE
1. Remove every synthetic clinical fallback. An empty comparison must return no observed changes plus explicit availability/completeness metadata, not a demo delta. Synthesis must remain faithful to actual evidence and clearly label inference.
2. Introduce/use a shared normalized evidence representation with patient/encounter ownership, immutable source ID, clinical concept/quantity, temporal status, confidence, and provenance. Reuse it for recall, summary, contradictions, and medication analysis instead of independently interpreting loose dictionaries.
3. Validate every source, including fields appended after primary synthesis and Ayurvedic/proxy/safety fields. Resolve immutable transcript/entity/document IDs under authorized scope. Missing sources cannot be substituted or marked document_extracted. Validate source type, ownership, quote/snippet origin, and coordinate availability; ID existence alone does not establish the claim is supported.
4. Coordinate transcript lookup changes: use immutable transcript IDs, required authorized encounter scope, deterministic result semantics, and no all-session memory scan/mock fallback. Update every citation producer and consumer contract.
5. Preserve all relevant clinical inputs. Aggregate complete HPI/history and medication lists with provenance, avoid arbitrary [:3]/first-item truncation, and explicitly report any section synthesis unavailable. Keep patient denials and conflicting evidence distinct.
6. Implement immutable or explicitly versioned summary drafts and clinician-review records. A read must not regenerate. Regeneration/lens changes create a new draft, preserve prior signed/reviewed versions and corrections, and require review as appropriate. Ask-back updates only its targeted draft field with the actual correlated answer.
7. Fix nested JSON persistence using immutable/deep-copy updates or reliable mutation tracking. Verify using fresh sessions. Record actor, original value, new value, source, timestamp, and version; require authenticated clinician identity. A single field edit must not certify unrelated unresolved fields or a future regenerated version.
8. Normalize medication mentions to ingredient sets and independent therapy occurrence IDs. Parse multiple mentions, brand aliases/case/spacing/strengths, combination formulations, scoped negation, stopped/historical use, and repeat evidence. Do not count a generic alias plus its brand as two drugs. Use supported catalog rules and surface unresolved normalization rather than claiming formulary clearance.
9. Use one medication detector implementation and a typed result: completed with alerts, completed without detected alerts within coverage, incomplete/unavailable. Preserve individual severity and evidence. Comparison history must use authorized patient records across relevant encounters with date/active-state rules, not merely the current session or highest confidence.
10. Persist contradictions with stable evidence-derived identity and review history. Separate clinician confirmation from error rejection, retain decisions across regeneration where evidence is unchanged, and invalidate/re-review when evidence changes. Normalize nullable values before string operations.
11. Validate model output inside a controlled typed boundary. Distinguish invalid/failed/empty responses. Failed optional safety checks must be visible in the summary's completeness/status, not silently omitted behind a successful response.

ACCEPTANCE TESTS
- Empty encounters produce no sample disease, prescription, change, or forged provenance.
- Unknown document/transcript IDs, wrong patient sources, unknown source types, empty transcript sets, and source-less claims cannot appear verified.
- PUT and resolution survive a fresh session, refresh, preview/export, and process restart; signed/reviewed versions remain immutable.
- Regeneration/lens changes preserve prior review and create the correct new draft; parallel edits detect version conflict instead of lost update.
- Four-plus medications and all answered history sections are retained, including conflict branches.
- Single generic+brand evidence is one therapy; warfarin and aspirin as separate mentions are both analyzed; atenolol is not removed by substring negation; combination ingredients and case/spacing variants are tested.
- Null generic names and unavailable model/rule data yield explicit supported outcomes, not crashes or fabricated clean checks.
- Contradictions include authorized prior visits and retain stable review status across refresh/restart.
- Clarification without a reply cannot modify the summary; actual reply updates the intended field only.

HANDOFF
Provide summary version/review APIs, immutable citation format, section enums for both lenses, medication check status/severity contract, contradiction action semantics, and export-ready reviewed-version selection rules.
```

## Assignment 6 — Consent-bound FHIR export and durable delivery

### Copyable task

```text
Repair clinical export identity, review semantics, FHIR construction, and retry delivery. Read Common instructions and consent/summary/contract handoffs.

PRIMARY OWNERSHIP
- backend/app/routes/fhir.py
- backend/app/services/fhir_builder.py and abdm_push.py
- Export queue schema additions coordinated with Assignment 1
- Export/consent/retry/FHIR validation tests and configuration documentation

AUDIT CONTEXT
FHIR endpoints default missing identity to rajesh.kumar@abdm, accept client-supplied identity/bundles, and never enforce patient consent or clinician affirmation. FHIRBundlePayload is unused. UI affirmation is not persisted or enforced server-side. The builder marks Composition final independent of review; verification labels are mapped simplistically, and every medication summary string is emitted as an active MedicationStatement, including alert/conflict prose. Examine reference resolution, escaping, resource/profile placement, and identity handling rather than assuming the bundle's resourceType proves conformance.

Push uses a fabricated bearer token and creates a random success reference based only on HTTP status. Retry calls push_bundle, which creates a new failed queue row on each failure while retaining the old row. Duplicate exports can multiply; consent revocation, version changes, and concurrent queue workers are not handled.

IMPLEMENTATION GUIDE
1. Resolve patient/encounter identity from authorized database records; reject unlinked or mismatched ABHA export. Remove all sample identity defaults from real builders/endpoints. Treat identifiers as identifiers rather than blindly using ABHA addresses as resource IDs.
2. Require authenticated clinician affirmation of an exact reviewed summary version and effective store_abdm consent. Revalidate consent when the queued job is delivered. Reject client bundles that bypass authoritative clinical/identity/review data; prefer server construction from a versioned snapshot.
3. Use canonical typed preview/export/affirmation/queue DTOs with explicit pending, delivered, failed, blocked, and unknown-delivery semantics. Preview does not imply consent, sign-off, or delivery.
4. Build clinical resources from structured reviewed data and preserve certainty/temporal status. Do not convert safety-alert prose, a stopped medication, or an unresolved contradiction into an active verified fact. Escape narrative markup, resolve references consistently, and validate against the chosen FHIR/ABDM profiles using authoritative specifications and appropriate tooling. Do not invent conformance claims.
5. Separate authenticated provider transport, queue insertion, and delivery attempts. Return actual acknowledgement/correlation identifiers, not generated strings masquerading as national record references. Missing production provider configuration must be explicit unavailable, with a separate isolated demo transport if needed.
6. Create one durable export job per consented reviewed snapshot/idempotency key. Claim jobs atomically with leases or row locking; update the same row on retry. Add bounded backoff, terminal/retryable error distinction, attempt history, and reconciliation of ambiguous timeout-after-acceptance. Do not assume a timeout proves the remote system rejected the request.
7. Coordinate queued PHI retention/cancellation with session privacy policy. Revoked consent or changed authorization blocks dispatch. Preserve the minimum permitted audit trail without retaining disallowed payloads indefinitely.

ACCEPTANCE TESTS
- No consent, refusal, revocation, no affirmation, wrong role, unlinked identity, wrong patient, stale summary version, and injected bundle all fail before transport.
- Export uses the exact persisted clinician-corrected version; preview and signed snapshot are consistent.
- Conflicts/alerts do not become active medications or confirmed diagnoses; references/narratives/profile structure pass the selected validator.
- Repeated failures increase attempts on one job, not queue length. Concurrent workers cannot duplicate delivery.
- Repeated client submissions use idempotency; network timeout after remote acceptance is handled without blind duplicate creation.
- Revocation before retry blocks the queued export; privacy cleanup follows the approved retention policy.
- All tests use injected transports and synthetic records; no real ABDM writes occur.

HANDOFF
Give frontend agents exact affirmation/preview/push/job-status examples, meaningful error states, and retry guidance. Document required production provider setup and any unperformed external conformance/interoperability validation.
```

## Assignment 7 — Kiosk flow, privacy teardown, offline behavior, and accessible input

### Copyable task

```text
Repair the real kiosk journey and browser lifecycle. Read Common instructions and current backend contracts.

PRIMARY OWNERSHIP
- frontend/src/App.jsx, contexts/SessionContext.jsx, hooks/useIdleTimeout.js
- frontend/src/components/kiosk/ identity/consent/navigation behavior
- frontend/src/components/interview/InterviewScreen.jsx, AyushInterview.jsx, UnvoicedConcern.jsx
- frontend/src/components/documents/ camera/upload/progress flows
- frontend/src/services/offlineQueue.js, voiceNavigation.js, and related active hooks/contexts
- frontend/src/utils/api.js/websocket.js if implementing shared transports, plus service-worker behavior
- Mounted/browser regressions for these paths
Assignment 8 owns tokens/shared visual styling and clinician/staff screens. Coordinate KioskButton and shared component changes; do not edit the same files concurrently.

AUDIT CONTEXT
Idle timers restart on every render because App passes a new onTimeout function. The effect also depends on isWarningActive and resets it when warning starts. The wipe awaits an unbounded network fetch before clearing local state; it omits IndexedDB mutation_queue, media/recognition cleanup, and in-flight requests that can repopulate state.

Identity/OTP failures return fabricated verified profiles. Failed session creation creates a local OPD ID, consent response status is ignored, and the flow continues. Socket handling recognizes only red_flag_triggered; resume/ack/paused/ask-back messages become question objects. Live completion never sets isCompleted. There is no question-pending guard, and disconnect leads to a local simulation that claims completion without persisted answers.

No production mutation calls offlineQueue.enqueue. The queue has no conflict/version/idempotency semantics, discards every 4xx including conflicts, races on isSyncing after awaiting getQueue, and uses hardcoded localhost health polling. Scan errors are logged but UI can stay in progress forever; missed status events are not reconciled.

Voice-only integration is a spacebar callback that only logs. Advertised languages exceed UI/ASR/TTS support; many selections fall back to Hindi with English recognition. Microphone/audio resources are not cleaned on every unmount. Browser storage/wipe was not live-verified during audit; you must obtain real browser evidence if tooling is available.

IMPLEMENTATION GUIDE
1. Build a shared configured HTTP/socket client with typed status/error handling, abort support, and deployment-safe origins. Do not scatter localhost URLs. Validate canonical server responses at meaningful boundaries; do not downgrade HTTP validation/auth errors into offline success.
2. Make identity and consent transitions reflect durable server state. Explicit manual/unverified intake is separate from verified identity. Retry safely using operation IDs; never manufacture demographics or pretend a failed consent write succeeded.
3. Implement a kiosk state machine for question, awaiting reply, pending clarification, emergency hold, acknowledged hold, resumed, completed, reconnecting, offline, and ended. Dispatch the canonical event union; include question ID/version and answer idempotency. Resume must clear/update the right alert and restore the real current question; other active holds remain enforced.
4. Make live completion use the server event/state, not a local question counter. Do not display sent to doctor until server persistence/handoff is confirmed. Failed delivery must remain visible and recoverable.
5. Repair idle logic around an absolute last-activity timestamp and stable callback refs. Warning changes must not reset expiry. Count supported voice interaction as activity. Define appropriate behavior during safety hold/assisted care using backend/product policy; do not wipe an active emergency merely because the screen was untouched.
6. On end/wipe immediately invalidate the session generation, hide/unmount PHI views, abort fetches and queued callbacks, stop recognition/audio/TTS/camera tracks, revoke object URLs, close sockets, and clear session-scoped React/browser stores. Block late results from repopulating a new patient session. Then perform bounded backend cleanup notification and display truthful status.
7. Coordinate whether offline PHI may be retained under consent. Purge disallowed queued payloads on wipe/revocation; retained pending work must be explicitly authorized, isolated from the next patient, and protected according to deployment requirements. Do not equate deleting two localStorage keys with full cleanup.
8. Implement offline actions through the shared mutation path, or explicitly block unsupported offline operations. Durable commands need encounter scope, immutable operation ID, expected entity/version, dependencies, and stable ordering. Never silently discard 401/403/409/422 results: retain or quarantine with a clear resolution path. Set sync ownership before awaits and handle multi-tab contention. The server must enforce idempotency/version conflicts as well.
9. Replace document fire-and-forget handling with checked upload/process/job responses, clear per-page pending/error/retry states, and status reconciliation on reconnect. Missing events cannot strand the workflow. Unmounts cancel local work without corrupting already accepted server jobs.
10. Wire a complete voice navigation/action system, not merely a classifier export. Every screen needs meaningful confirm/deny/back/repeat/help and control equivalents; avoid substring matches such as a short confirmation fragment matching unrelated speech. Provide supported recovery when voice services are unavailable without claiming voice-only completion.
11. Define one supported-language registry consistent with prompt dictionaries, UI strings, ASR, TTS, and script direction. Complete or remove unsupported selections; do not silently switch languages. Translate patient-facing pending/error/safety messages and test them.

ACCEPTANCE TESTS
- Mounted fake-timer tests reach warning/expiry exactly once despite renders; user/voice activity extends correctly; warning does not self-reset.
- Browser devtools/automation checks React-visible state, sessionStorage/localStorage, IndexedDB, Cache Storage where used, active sockets, microphone/camera/audio, and late request callbacks after wipe. Test offline and slow-end-request cases. Document precisely what can/cannot be observed.
- Identity/OTP/consent failures cannot create verified or durable-success UI states.
- Every safety/control event renders correctly; the live interview completes; double taps/stale replies cannot advance twice.
- Disconnect/reconnect preserves the real question/hold; offline capture either persists valid commands or explicitly blocks rather than simulating success.
- Two conflicting offline edits are surfaced/resolved by explicit policy, retries are idempotent, 4xx actions are not silently deleted, and one patient's queue cannot appear in the next patient's session.
- Upload failure, processing 500, lost socket events, partial multi-page failure, retry, and navigation away all have correct UI and persisted outcomes.
- Complete an end-to-end no-touch journey across all screens, plus denial/back/error recovery; test each advertised language's visible and spoken paths.

HANDOFF
Document the kiosk state machine, shared transports, queue conflict policy, supported language matrix, wipe verification evidence, and any accessibility constraints that still prevent a complete voice-only journey.
```

## Assignment 8 — Doctor/staff workflows, evidence UI, and design-system consistency

### Copyable task

```text
Repair clinician/staff workflows against the actual backend contracts and make shared UI derive from canonical tokens. Read Common instructions and backend/frontend transport handoffs.

PRIMARY OWNERSHIP
- frontend/src/pages/DoctorDashboard.jsx and StaffAlerts.jsx if active
- frontend/src/components/doctor/ and patient-facing summary/evidence components used there
- frontend/src/components/interview/StaffAlertPanel.jsx and RedFlagAlert.jsx
- frontend/src/styles/tokens.css/global.css, shared KioskButton/KioskCard styling (coordinate Assignment 7)
- frontend/src/components/visualization/ rendering consumers
- Mounted/browser clinician, accessibility, token, and contract regressions

AUDIT CONTEXT
DoctorDashboard defaults unlinked identity to Rajesh and ABHA rajesh.kumar@abdm. SummaryView regenerates on mount rather than reading a reviewed version. Ayurvedic section keys do not match output; family_hx/personal_hx disappear under the family_personal whitelist. Transcript responses omit metadata that caregiver/unvoiced consumers expect. ABDM fetch reads documents_fetched/entities_extracted even though the server returns records_retrieved/extracted_entities_count; exceptions display success.

ClickToSource uses a reusable question ID without encounter scope, keeps request state without robust cancellation, and invents fallback question/answer/crop metadata. Unknown image requests can appear as plausible evidence. AskBackPanel immediately says received after an endpoint that previously fabricated a reply. ConfirmPush relies on a local checkbox rather than server affirmation and defaults patient identity. Preview opens only after the request completes, hiding its pending indicator while the first request is slow.

Staff acknowledgement ignores HTTP status; no alerts means the panel hides, including disconnected state. There is no durable alert replay/reconnection UX. Failed/empty polypharmacy fetch renders formulary verification; alerts depend on medication section presence and flatten severity into text.

The four original badge foregrounds use tokens, but backgrounds/borders are hardcoded; doctor_edited is hardcoded purple with no canonical token. --touch-target-min is 56px but no component consumes it; shared small buttons are 48px. Clickable badges are spans without keyboard semantics. Hardcoded component palettes ignore high contrast.

IMPLEMENTATION GUIDE
1. Require authenticated clinician/staff state from the real access system. Remove sample patient/session identity defaults; show unlinked identity explicitly and disable export when disallowed. UI mode toggles never confer authorization.
2. Fetch existing summaries and versions on view; generate only on an explicit supported action. Show draft/reviewed/signed status and version conflicts. Preserve doctor corrections across refresh, lens changes, targeted clarification, and exports using server semantics.
3. Render all canonical sections for both lenses. Unknown sections must be visible as unsupported/unclassified, not silently dropped. Consume complete source/proxy/concern metadata from the actual response; coordinate any missing fields with backend owners.
4. Use immutable, authorized source IDs and scope. Distinguish pending, unavailable, forbidden, and found evidence. Never display a manufactured sample crop/quote/confidence. Cancel or ignore stale source fetches so rapidly switching citations cannot display a different source's answer. Render unknown bbox/date/confidence honestly.
5. Implement ask-back pending/delivered/answered/failed states using correlated request IDs and actual replies. Keep optional clinician-entered patient responses explicitly attributed; do not invent one. Show the affected summary version and require appropriate review.
6. Implement server-recorded affirmation for the exact summary version before export. Use real consent/identity eligibility and queue/job status. A queued job is not delivered; a timeout is not verified rejection; retry uses the existing idempotent job. Show preview pending immediately and all error states visibly.
7. Keep staff connectivity visible even with zero alerts. Reconnect/reconcile active alerts from durable state, deduplicate by event ID, and distinguish acknowledgement from dismissal. Check response status, show pending/error, and never remove or acknowledge an alert just because fetch resolved.
8. Render medication check status independent of summary medication sections: unavailable/incomplete, completed with alerts, or completed without detected alerts within declared coverage. Preserve per-alert severity and provenance. No fabricated formulary-clearance message on empty/error responses.
9. Extend tokens for doctor-edited and all semantic badge foreground/background/border states. Derive colors from tokens, including high-contrast overrides. Consolidate repeated hardcoded component colors into the semantic system without changing clinical meaning.
10. Enforce min-width/min-height var(--touch-target-min) on every interactive kiosk/shared control, including compact buttons, badges, dismiss icons, inputs, and modal controls. Use semantic buttons/labels, keyboard activation, visible focus, accessible names, dialog focus management, and touch-friendly hit regions. Do not solve the issue by reducing the canonical token.
11. Coordinate localization with Assignment 7. Patient-facing content must use the selected supported language; staff-only English can remain only if the product explicitly scopes it that way. Do not treat bilingual hardcoded text as universal multilingual support.

ACCEPTANCE TESTS
- Unlinked patients never acquire another person's ABHA identity; wrong-role controls cannot execute protected operations.
- Doctor edits survive refresh and exported snapshots; stale edits/sign-off receive visible version conflicts.
- Every allopathic/Ayurvedic canonical section appears; caregiver/unvoiced metadata is displayed when present.
- Cross-patient, missing, forbidden, and rapidly switched sources show correct evidence/error without fake fallback data.
- Ask-back waits for the actual response; pending/disconnected/error cases never say answered.
- Preview, affirmation, push, queued retry, delivered status, failure, revocation, and changed summary version have accurate pending/error/eligibility UI.
- Staff socket outage remains visible with no alerts; alerts replay, deduplicate, and cannot falsely acknowledge on 500/403 responses.
- Failed medication checking cannot look clean and alerts appear even without medication summary fields.
- Browser-computed target sizes honor 56px at all supported sizes; keyboard/focus/modal tests pass; theme changes affect badge/background/border states through tokens.

HANDOFF
Document workflow/state changes, token additions, actual supported accessibility/localization behavior, browser evidence, and any outstanding backend contract mismatch rather than adding client-side compatibility guesses.
```

## Assignment 9 — Adversarial integration, evaluation, and launch evidence

### Copyable task

```text
Act as the final independent repair/verification owner. Read Common instructions, all eight assignments, their diffs, and handoffs. Do not trust their completion claims or only rerun the same happy-path tests. Fix remaining seams and report actual launch readiness.

PRIMARY OWNERSHIP
- Cross-domain integration tests, browser journeys, migration/contract checks, benchmark harnesses
- backend/tests/, frontend test infrastructure, CI verification, and evidence reports
- Small integration fixes in domain files after checking ownership and preventing concurrent edits
- Deployment/runtime verification directly relevant to repaired behavior

AUDIT CONTEXT
Existing frontend tests mostly check exports/constants. The low-confidence test copies production logic without invoking processing. Staff broadcast tests accept zero delivered recipients. Summary edit tests validate returned text but not a fresh read. Smart Recall tests inject context directly or test the loader separately, missing the unwired route. Source tests accept keys or nonempty JPEGs without checking the actual patient's evidence.

OCR accuracy compares annotations with themselves. Semigran-style completeness adds downstream sections to a set without asking them. Complaint categories pain/general/psych/obgyn are called triage concordance. False-positive audit calls scan_text only, omitting confirmation and staff delivery; it has no sensitivity claim. Test setup uses application database settings and create_all, concealing Alembic drift and risking development data. Existing stress tests do not establish multi-worker recovery or realistic slow-inference behavior.

IMPLEMENTATION GUIDE
1. Create a requirements-to-evidence matrix covering every defect in Assignments 1–8 and their reused instances. Record file/commit, repaired behavior, regression test, runtime evidence, and any unverified dependency. Do not collapse missing evidence into a green check.
2. Make tests hermetic: isolated temp SQLite/PostgreSQL databases upgraded with Alembic, synthetic fixtures, deterministic injected providers, disabled unintended network, and explicit environment configuration. Test instance/bulk/direct SQL, not just ORM happy paths. Do not read existing clinical databases or real credentials.
3. Add contract checks for all six core shapes plus actual WebSocket envelopes, clinician review, scan job, export job, and error states. Validate real endpoint JSON against canonical models and frontend consumers. Detect duplicate method/path registrations and schema-generation drift.
4. Re-run full session handoff → consent → scan → real-context interview → emergency hold → staff replay/ack/dismiss → summary → edit/resolve → clarification → source lookup → affirmation/export → end/wipe. Include multilingual/proxy/AYUSH paths and more than three medications. Inspect persistence using fresh sessions and after process restart.
5. Add adversarial cross-patient/resource tests, expired/denied/revoked consent, forged staff identity, unlinked ABHA, stale question/version, duplicate mutation, multiple alerts, and queue replay/conflict cases. Use real domain logic; mock only external boundaries, clocks, and controlled failures.
6. Exercise malformed model JSON and schema-invalid valid JSON at each call site, including missing keys, nulls, wrong enums, string booleans, out-of-range/NaN confidence, bad bbox, invalid sources, and truncated output. Ensure unknown clinical state remains unknown and safety candidates are not silently erased.
7. Use mounted frontend and real browser automation. Verify all API/control events and slow/failing network states, computed touch targets, high contrast, keyboard focus, supported languages, and no-touch navigation. After wipe inspect relevant application stores, IndexedDB, Cache Storage, sockets, media tracks, and late callbacks. Browser memory claims must be limited to what is actually observable; do not claim literal heap erasure without evidence.
8. Replace misleading evaluations. OCR must process held-out actual document images then compare structured predictions against independent ground truth with appropriate one-to-one matching, values/units/dates/bboxes, and per-type errors. Elicitation must execute full conversations and measure actually elicited information. Emergency evaluation must cover positives/negatives, language/context, malformed confirmation, and delivery/recovery. Separate complaint routing from clinical triage; verify dataset provenance before calling a corpus Semigran-45.
9. Save reproducible evaluation metadata: git revision, dataset hash/provenance, model/version, prompt hash, provider mode, seed where relevant, configuration, timestamp, and raw aggregate results. Never treat deterministic fixture-mode metrics as live-model accuracy. If external/model/image data is unavailable, mark that evaluation blocked/unverified rather than fabricate a number.
10. Exercise multiple concurrent kiosks with slow providers, concurrent staff actions, duplicate connections, process restart, and more than one worker if supported. Verify event-loop responsiveness, bounded work/memory, delivery recovery, idempotent export jobs, and unbounded history/queue risks. If the implementation supports only one worker, make that limitation explicit and enforceable until repaired.
11. Validate deployment against a migrated PostgreSQL instance where available, production provider gating, schema readiness, frontend/backend origins, and diagnostic access. Do not deploy or send real records merely to produce evidence.
12. Fix concrete integration failures; return larger domain defects to the responsible owner with a minimal reproduction and continue independent verification. Do not resolve failures by weakening tests, increasing arbitrary sleeps, disabling auth, or reintroducing samples.

FINAL OUTPUT
Create an audit closure report containing:
- Defect-to-fix-to-test matrix, grouped by the original eight audit sections.
- Exact tests/evaluations run and results, with artifact paths and revision/configuration.
- Remaining confirmed bugs, unverified external assumptions, and unavailable checks, each with impact and next action.
- Migration/deployment/rollback instructions and any irreversible-data-recovery limitations.
- Clear launch recommendation supported by evidence, especially emergency delivery, correct patient identity, persisted doctor review, consent enforcement, and privacy teardown.

DO NOT declare launch readiness merely because the old benchmark/test suite passes. The acceptance criterion is correct behavior under the adversarial conditions that exposed the original defects.
```

## Coverage cross-check

| Original audit area | Primary assignment(s) | Final verification |
| --- | --- | --- |
| Alembic/ORM drift, consent migration, append-only enforcement, FKs/nullability | 1, 2 | 9: fresh and historical migration tests; direct SQL; retention |
| Six core contracts, enums, duplicate routes, source metadata | 1, 3, 4, 5, 6 | 9: actual response/event and consumer validation |
| Red flags, malformed Gemini JSON, delivery/holds, recall thresholds | 3 | 9: failure injection and end-to-end recovery |
| Fabricated clinical data, hallucinated citations, summary truncation | 4, 5 | 9: empty/invalid evidence and held-out cases |
| Medication aliases/negation/combinations, contradictions, review identity | 5 | 9: normalization, history, refresh/restart |
| Consent/authentication, identity fabrication, session privacy | 2, 6, 7 | 9: cross-patient, revoked consent, browser teardown |
| Lab numeric/unit/demographic errors and invalid dates | 4 | 9: real pipeline values and timezone/date cases |
| Lost doctor edits, regeneration overwrite, review/version conflicts | 5, 8 | 9: fresh reads and export snapshots |
| FHIR identity/consent/sign-off, mock transport, duplicated retry jobs | 6, 8 | 9: blocked export, idempotency, provider validation |
| Idle timer, offline queue/conflicts, socket/media lifecycle | 3, 7, 8 | 9: mounted timers, real browser, restart/concurrency |
| Voice-only, languages, token colors, 56px targets, pending/error UI | 7, 8 | 9: computed styles and complete user journeys |
| Weak tests, misleading benchmarks, unsafe test DB setup | Every owner, then 9 | 9: independent artifacts and corrected methodology |
| Async inference blocking, process-local state, shared evidence architecture | 3, 5, 6 | 9: multiple kiosks/workers, slow providers, durable recovery |
