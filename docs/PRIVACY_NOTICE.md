# Privacy Notice - Bank Statements Processor

**Last Updated:** 2026-01-29
**Version:** 1.1.0

## 1. Introduction

This Privacy Notice explains how the Bank Statements Processor ("the Application") handles your financial data when you use it to process bank statement PDFs. This document fulfills the transparency requirements of the General Data Protection Regulation (GDPR) Articles 13-14.

**Important:** This application processes data **locally on your machine only**. No data is transmitted to external servers or third parties.

---

## 2. Data Controller

When you use this application, **you are the data controller**. This means:

- You determine what data is processed
- You control how long data is retained
- You are responsible for compliance with applicable data protection laws
- The application is a tool you use to process your own data

**Application Developer:**
- GitHub: [@longieirl](https://github.com/longieirl)
- Repository: [github.com/longieirl/bankstatements](https://github.com/longieirl/bankstatements)

**Note:** The developer provides the software tool but does not process, access, or control your data.

---

## 3. What Data is Processed

The application processes the following information from your bank statement PDFs:

### Personal Data
- **Transaction dates**: When transactions occurred
- **Transaction descriptions**: Merchant names, transaction details
- **Transaction amounts**: Debit and credit amounts
- **Account balances**: Running balance information
- **Any other data present in your bank statements**

### Processing Activity Metadata (Optional)
When activity logging is enabled (`LOGS_DIR` configured), the application records:
- Number of PDFs processed
- Number of transactions extracted
- Processing timestamps
- File deletion events (file names only, no transaction data)

**What is NOT collected:**
- Account numbers (unless present in transaction descriptions)
- Personal identifiers (unless present in transaction descriptions)
- No data is sent to external servers
- No analytics or telemetry

---

## 4. Legal Basis for Processing

Your legal basis for processing depends on your use case:

### For Personal Use (Article 6.1.f - Legitimate Interest)
If you are processing your own bank statements for personal financial management, your legal basis is **legitimate interest**.

### For Business Use (Article 6.1.b - Contract or Article 6.1.c - Legal Obligation)
If you are:
- A business processing employee expenses → **Contract** (employment relationship)
- An accountant processing client data → **Contract** (service agreement) + **Consent**
- Processing for tax compliance → **Legal obligation**

### Consent (Article 6.1.a)
If you are processing data on behalf of others (e.g., family members), you must obtain their explicit consent.

---

## 5. Purpose of Processing

The application processes data for the following purposes:

1. **PDF Extraction**: Extract transaction data from bank statement PDFs
2. **Data Transformation**: Convert extracted data to structured formats (CSV, JSON, Excel)
3. **Duplicate Detection**: Identify and flag duplicate transactions
4. **Data Analysis**: Calculate totals and generate monthly summaries
5. **File Management**: Store output files locally on your system
6. **Audit Trail**: Record processing activities for accountability (optional)

**Purpose Limitation:** Data is only used for the purposes you specify. The application does not use your data for any other purpose.

---

## 6. Data Storage and Retention

### Local Storage
- **Input Files**: Stored in `input/` directory until you delete them
- **Output Files**: Stored in `output/` directory according to retention policy
- **Activity Logs**: Stored in `logs/` directory (metadata only, no transaction data)

### Retention Policy
You can configure data retention in two ways:

#### Option 1: Automatic Retention Policy
Set `DATA_RETENTION_DAYS` environment variable:
```bash
DATA_RETENTION_DAYS=90  # Files older than 90 days are eligible for cleanup
```

#### Option 2: Manual Deletion
You can delete data at any time using:
```bash
make delete-data           # Delete all output files
make cleanup-old-data      # Delete files older than retention period
```

### Recommended Retention Periods
- **Personal use**: 90-365 days (align with bank statement availability)
- **Business use**: Follow your organization's data retention policy
- **Tax purposes**: Consult your local tax authority (often 5-7 years)

### Data Minimization
The application only processes data present in your input PDFs. It does not collect additional data.

---

## 7. Your Data Subject Rights (GDPR Articles 15-22)

As the data controller, you have the following rights:

### Right of Access (Article 15)
- **What**: Access to all processed data
- **How**: Output files are in `output/` directory, readable in any text editor

### Right to Rectification (Article 16)
- **What**: Correct inaccurate data
- **How**: Edit CSV/JSON/Excel output files directly, or correct source PDFs and reprocess

### Right to Erasure (Article 17)
- **What**: Delete your data ("Right to be Forgotten")
- **How**:
  ```bash
  make delete-data              # Delete all output files
  rm -rf input/*.pdf             # Delete input PDFs
  rm -rf logs/                   # Delete activity logs
  ```

### Right to Restriction (Article 18)
- **What**: Pause processing
- **How**: Don't run the application; keep data in `input/` directory without processing

### Right to Data Portability (Article 20)
- **What**: Receive data in machine-readable format
- **How**: Output files are already in portable formats (CSV, JSON, Excel)

### Right to Object (Article 21)
- **What**: Object to processing
- **How**: Stop using the application and delete all data

### Rights Related to Automated Decision-Making (Article 22)
- **Not applicable**: This application does not make automated decisions that produce legal effects

---

## 8. Data Security Measures (Article 32)

The application implements the following security measures:

### Technical Measures
1. **Local Processing**: No network transmission of financial data
2. **Secure Deletion**: Files are overwritten 3 times before deletion (DoD 5220.22-M standard)
3. **Optional Encryption**: AES-256-GCM encryption for output files (opt-in)
4. **Secure File Permissions**: Encryption keys stored with chmod 600 (owner read/write only)

### Organizational Measures
1. **Privacy by Design**: Security and privacy built into the application
2. **Data Minimization**: Only processes data you provide
3. **Transparency**: Open-source code, auditable by anyone
4. **Activity Logging**: Audit trail of processing operations (optional)

### Encryption at Rest (Optional)
Enable encryption with:
```bash
ENCRYPT_OUTPUT=true
```

This encrypts all output files with AES-256-GCM. See [ENCRYPTION.md](ENCRYPTION.md) for details.

### Limitations
- **Physical Security**: You are responsible for securing your device
- **Operating System Security**: Keep your OS and security software updated
- **Backup Security**: Ensure backups of output files are secured appropriately

---

## 9. Data Sharing and Transfers

### No External Data Sharing
The application does **NOT**:
- Send data to external servers
- Upload data to cloud services
- Share data with third parties
- Transmit data over the network
- Use analytics or telemetry services

### Your Responsibility
If you choose to:
- Email output files
- Upload files to cloud storage
- Share files with others

**You are responsible** for ensuring appropriate security and legal compliance.

---

## 10. International Data Transfers

**Not applicable** - This application processes data locally on your device. No international data transfers occur.

If you move output files across borders, you must ensure compliance with applicable data protection laws.

---

## 11. Data Breach Notification

Since you are the data controller:

- **Your responsibility**: Report data breaches to relevant authorities and affected individuals if required by law
- **Application security**: Report security vulnerabilities to the developer via [GitHub Issues](https://github.com/longieirl/bankstatements/issues)

---

## 12. Processing Activity Records (Article 30)

The application can maintain processing records to help you comply with Article 30:

### Enable Activity Logging
```bash
LOGS_DIR=logs  # Default, creates logs/processing_activity.jsonl
```

### What is Logged
- Processing timestamp
- Number of PDFs processed
- Number of transactions extracted
- Duration of processing
- Deletion events (file names, reasons, dates)
- Encryption operations

### What is NOT Logged
- Transaction details
- Account numbers
- Personal identifiers
- Sensitive financial data

---

## 13. Children's Privacy

This application is not intended for use by individuals under 16 years of age. If you are processing data of minors, ensure you have appropriate legal authority.

---

## 14. Changes to This Privacy Notice

This privacy notice may be updated when new features are added. Check the "Last Updated" date at the top of this document.

**Version History:**
- v1.1.0 (2026-01-29): Added GDPR compliance features (retention, audit log, encryption)
- v1.0.0 (2024-01-28): Initial release

---

## 15. Compliance Checklist

Use this checklist to ensure GDPR compliance:

- [ ] **Lawful Basis**: Identify your legal basis for processing (Section 4)
- [ ] **Data Minimization**: Only process necessary bank statements
- [ ] **Retention Policy**: Configure `DATA_RETENTION_DAYS` or plan manual deletion
- [ ] **Security**: Enable encryption if processing sensitive data (`ENCRYPT_OUTPUT=true`)
- [ ] **Activity Log**: Enable if you need audit trail (`LOGS_DIR=logs`)
- [ ] **Data Subject Rights**: Know how to exercise rights (Section 7)
- [ ] **Deletion Procedure**: Test deletion commands before production use
- [ ] **Backup Security**: Ensure backups are encrypted and access-controlled
- [ ] **Third-Party Sharing**: If sharing files, ensure appropriate safeguards
- [ ] **Legal Review**: For business use, consider legal counsel review

---

## 16. Questions and Contact

### For Application Usage
- GitHub Issues: [github.com/longieirl/bankstatements/issues](https://github.com/longieirl/bankstatements/issues)
- Documentation: See [README.md](../README.md), [GDPR_COMPLIANCE.md](GDPR_COMPLIANCE.md)

### For Legal/Privacy Questions
Since you are the data controller, consult with:
- Your legal counsel (for business use)
- Your Data Protection Officer (if applicable)
- Your local data protection authority

---

## 17. Supervisory Authority

If you have concerns about how you are processing data using this application, you can contact your local data protection supervisory authority:

### European Union
Find your authority: [https://edpb.europa.eu/about-edpb/about-edpb/members_en](https://edpb.europa.eu/about-edpb/about-edpb/members_en)

### United Kingdom
Information Commissioner's Office (ICO): [https://ico.org.uk](https://ico.org.uk)

### Other Jurisdictions
Consult your local data protection authority website.

---

## 18. Disclaimer

This privacy notice is provided for informational purposes and does not constitute legal advice. For legal compliance guidance, consult a qualified attorney specializing in data protection law.

The application developer makes no warranties regarding GDPR compliance and disclaims liability for how you use the software. **You are responsible for your own compliance** with applicable data protection laws.

---

## 19. Open Source License

This application is open-source software. See [LICENSE](../LICENSE) for terms of use.

**Key Points:**
- Software provided "as is" without warranty
- You assume all risks of use
- Developer not liable for data breaches or compliance failures
- You are responsible for security and legal compliance

---

## Summary

✅ **Data stays local** - No external transmission
✅ **You are in control** - You are the data controller
✅ **Transparent processing** - Open-source, auditable code
✅ **Security features** - Encryption, secure deletion, activity logging
✅ **Flexible retention** - Configure automatic cleanup or manual deletion
✅ **Your responsibility** - Ensure your own GDPR compliance

For detailed implementation guidance, see:
- [GDPR_COMPLIANCE.md](GDPR_COMPLIANCE.md) - Full compliance assessment
- [GDPR_QUICK_REFERENCE.md](GDPR_QUICK_REFERENCE.md) - Quick reference guide
- [ENCRYPTION.md](ENCRYPTION.md) - Encryption setup and usage
