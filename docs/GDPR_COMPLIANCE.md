# GDPR Compliance Assessment

## Overview

This document assesses the bankstatements application's compliance with the **General Data Protection Regulation (GDPR)** - EU Regulation 2016/679 on data protection and privacy.

## What is GDPR?

The General Data Protection Regulation is EU law governing data protection and privacy. It applies to any organization processing personal data of EU residents, regardless of where the organization is located.

### Key GDPR Principles (Article 5)

1. **Lawfulness, Fairness, Transparency** - Legal basis for processing, clear communication
2. **Purpose Limitation** - Data collected for specific, explicit purposes only
3. **Data Minimization** - Only process data that is necessary
4. **Accuracy** - Keep personal data accurate and up to date
5. **Storage Limitation** - Delete data when no longer needed
6. **Integrity and Confidentiality** - Appropriate security measures
7. **Accountability** - Demonstrate compliance

## Current Compliance Status

### ✅ COMPLIANT Areas

#### 1. Data Minimization (Article 5.1.c)
**Status:** ✅ **COMPLIANT**

- Application processes only transaction data from bank statements
- No collection of unnecessary personal information
- Processing is limited to what's needed for statement consolidation
- Column names logged, but not values (see SECURITY_LOGGING.md)

#### 2. Security Measures (Article 32)
**Status:** ✅ **COMPLIANT**

- No sensitive data in application logs (DEBUG or otherwise)
- File names not logged (preventing PII exposure)
- Transaction values never logged
- Docker containerization provides isolation
- Type safety enforced with MyPy strict mode

#### 3. Data Portability (Article 20)
**Status:** ✅ **COMPLIANT**

- Outputs in standard formats (CSV, JSON, Excel)
- Data can be easily exported and transferred
- No proprietary formats that lock in data

#### 4. Transparency (Article 12-14)
**Status:** ⚠️ **PARTIAL** - See Recommendations

- README.md explains what application does
- No explicit privacy notice for data subjects
- Recommendation: Add PRIVACY_NOTICE.md

### ⚠️ AREAS NEEDING ATTENTION

#### 1. Storage Limitation (Article 5.1.e)
**Status:** ⚠️ **NEEDS IMPROVEMENT**

**Current State:**
- Output files stored indefinitely in `/output` directory
- No automatic deletion policy
- Files: `bank_statements.csv`, `bank_statements.json`, `bank_statements.xlsx`, `duplicates.json`, `monthly_summary.json`

**Risk:**
- Violates "storage limitation" principle
- Personal/financial data retained longer than necessary

**Recommendations:**
1. **Add data retention configuration:**
   ```bash
   DATA_RETENTION_DAYS=90  # Auto-delete after 90 days
   ```

2. **Implement cleanup script:**
   ```bash
   scripts/cleanup_old_data.py --older-than 90
   ```

3. **Add to documentation:**
   - Clear retention policy
   - Instructions for manual deletion
   - Compliance with local regulations

#### 2. Right to Erasure (Article 17 - "Right to be Forgotten")
**Status:** ⚠️ **NEEDS IMPROVEMENT**

**Current State:**
- No built-in data deletion functionality
- Users must manually delete files from `/output`
- No audit trail of deletions

**Recommendations:**
1. **Add deletion command:**
   ```bash
   make delete-data  # Securely delete all output files
   ```

2. **Implement secure deletion:**
   - Overwrite files before deletion
   - Log deletion events (date/time, not content)
   - Provide confirmation to user

3. **Document deletion process:**
   - How to delete specific processing runs
   - How to verify deletion
   - Retention of deletion logs for accountability

#### 3. Lawfulness of Processing (Article 6)
**Status:** ⚠️ **NEEDS CLARIFICATION**

**Current State:**
- No explicit documentation of legal basis for processing

**Legal Basis Options for Bank Statement Processing:**

a) **Consent (6.1.a)** - Most likely basis for this application
   - User voluntarily provides PDF files
   - User initiates processing
   - Recommendation: Add consent notice

b) **Contract (6.1.b)** - If processing is service delivery
   - If application is part of financial service

c) **Legitimate Interest (6.1.f)** - For business use
   - Personal financial management
   - Accounting/bookkeeping purposes
   - Must document legitimate interest assessment

**Recommendations:**
1. Add PRIVACY_NOTICE.md explaining:
   - What data is processed (transaction details from PDFs)
   - Why it's processed (consolidation, deduplication, analysis)
   - Legal basis (likely: user consent via voluntary upload)
   - How long it's kept (recommend: until user deletes)
   - User rights (access, deletion, portability)

#### 4. Data Protection by Design (Article 25)
**Status:** ✅ **GOOD** but can improve

**Current State:**
- Security measures implemented (no logging of sensitive data)
- Containerization provides isolation
- No external data transmission

**Improvements:**
1. **Add encryption at rest option:**
   ```bash
   ENCRYPT_OUTPUT=true  # Encrypt output files
   ENCRYPTION_KEY_PATH=/path/to/key
   ```

2. **Add anonymization option:**
   ```bash
   ANONYMIZE_DETAILS=true  # Redact merchant names from output
   ```

3. **Add data masking for testing:**
   ```bash
   MASK_AMOUNTS=true  # Replace amounts with dummy values
   ```

### ❌ NON-COMPLIANT Areas

#### 1. No Privacy Notice
**Status:** ❌ **MISSING**

**Required:** Privacy notice explaining data processing

**Action Required:**
Create `PRIVACY_NOTICE.md` with:
- Identity of data controller
- Purpose of processing
- Legal basis
- Data retention period
- User rights (access, rectification, erasure, portability)
- Right to withdraw consent
- Right to lodge complaint with supervisory authority

#### 2. No Data Processing Records
**Status:** ❌ **MISSING** (Required for organizations with >250 employees or regular processing)

**Recommended:**
- Log processing activities (file count, date, duration)
- Do NOT log sensitive data
- Keep for accountability purposes

**Example:**
```
2024-01-28 10:30:15 - Processing started - 5 PDFs
2024-01-28 10:30:45 - Processing completed - 150 transactions
2024-01-28 10:30:45 - Output generated - CSV, JSON, Excel
```

## GDPR User Rights

### Summary of Rights & Current Support

| Right | Article | Current Support | Notes |
|-------|---------|----------------|-------|
| Right to be Informed | 13-14 | ⚠️ Partial | Need privacy notice |
| Right of Access | 15 | ✅ Yes | All data in accessible formats |
| Right to Rectification | 16 | ✅ Yes | Users can edit output files |
| Right to Erasure | 17 | ⚠️ Manual | Need automated deletion |
| Right to Restrict Processing | 18 | ✅ Yes | User controls when processing runs |
| Right to Data Portability | 20 | ✅ Yes | CSV, JSON, Excel outputs |
| Right to Object | 21 | ✅ Yes | User can stop using application |
| Automated Decision Making | 22 | ✅ N/A | No automated decisions made |

## Implementation Status

### ✅ IMPLEMENTED Features

1. **Privacy Notice** ✅
   - Complete GDPR-compliant privacy notice
   - Located at [PRIVACY_NOTICE.md](PRIVACY_NOTICE.md)
   - Covers all Articles 13-14 requirements

2. **Data Retention Policy** ✅
   - Configurable retention period via `DATA_RETENTION_DAYS`
   - Automated cleanup with `make cleanup-old-data`
   - Documented in README.md and .env.example

3. **Right to Erasure (Data Deletion)** ✅
   - `make delete-data` command with confirmation
   - Secure file deletion (3x overwrite)
   - CLI tool at `scripts/delete_data.py`
   - Auto-cleanup option via `AUTO_CLEANUP_ON_EXIT`

4. **Processing Activity Log** ✅
   - JSONL audit trail in `logs/processing_activity.jsonl`
   - Logs processing, deletion, and encryption events
   - No sensitive data stored in logs
   - Configurable via `LOGS_DIR`

5. **Encryption at Rest** ✅
   - Optional AES-256-GCM encryption
   - Enabled via `ENCRYPT_OUTPUT=true`
   - Automatic key generation and management
   - Documented in [ENCRYPTION.md](ENCRYPTION.md)

### 📋 Compliance Checklist

- [x] Create PRIVACY_NOTICE.md
- [x] Document legal basis for processing
- [x] Implement data retention policy
- [x] Add automated data deletion feature
- [x] Create processing activity log
- [x] Add encryption at rest option
- [x] Test deletion procedures
- [x] Update README.md with privacy information
- [x] Add GDPR_QUICK_REFERENCE.md
- [ ] Consider Data Protection Impact Assessment (DPIA) - User responsibility
- [ ] Review with legal counsel (if business use) - User responsibility

### 🟢 FUTURE ENHANCEMENTS (Optional)

6. **Anonymization Features**
   - Optional data masking
   - Useful for testing/demos
   - Privacy-enhancing technology

7. **Privacy Impact Assessment (PIA)**
   - Document data flows
   - Assess privacy risks
   - Mitigation measures

8. **Key Rotation Support**
   - Automatic encryption key rotation
   - Key versioning

9. **Hardware Security Module (HSM) Integration**
   - Enterprise key management
   - Hardware-backed encryption

## Special Considerations

### 1. Self-Hosted / Personal Use

If application is for **personal use only** (user processing their own data):
- GDPR still applies but more lenient
- User is both "data controller" and "data subject"
- Most requirements still good practice
- Privacy notice less critical

### 2. Business Use

If application processes **others' data** (e.g., accountant processing client statements):
- Full GDPR compliance required
- Data Processing Agreement (DPA) may be needed
- Must document legal basis
- Must honor data subject rights

### 3. Location of Processing

- Application runs locally (not cloud)
- No data transfer outside user's control
- Reduces GDPR complexity
- No international transfer issues

## Compliance Checklist

Use this checklist to track compliance efforts:

- [ ] Create PRIVACY_NOTICE.md
- [ ] Document legal basis for processing
- [ ] Implement data retention policy
- [ ] Add automated data deletion feature
- [ ] Create processing activity log
- [ ] Add encryption at rest option
- [ ] Test deletion procedures
- [ ] Update README.md with privacy information
- [ ] Consider Data Protection Impact Assessment (DPIA)
- [ ] Review with legal counsel (if business use)

## Useful Resources

- **GDPR Official Text:** https://gdpr-info.eu/
- **ICO (UK) GDPR Guidance:** https://ico.org.uk/for-organisations/guide-to-data-protection/
- **EU GDPR Portal:** https://ec.europa.eu/info/law/law-topic/data-protection_en
- **EDPB Guidelines:** https://edpb.europa.eu/our-work-tools/general-guidance_en

## Contact for Data Privacy Questions

For questions about data processing in this application:
- Open an issue: https://github.com/longieirl/bankstatements/issues
- Review documentation: docs/PRIVACY_NOTICE.md (to be created)

---

**Last Updated:** 2026-01-28
**Version:** 1.0.0
**Next Review:** 2026-07-28 (6 months)

**Disclaimer:** This assessment provides general guidance. For specific legal compliance, consult with a qualified data protection professional or legal advisor.
