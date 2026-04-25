# Formal Reference: Domain Glossary

## 1. Why a Glossary?

In projects with AI agents, inconsistent terminology is a vector of silent errors. An agent that uses "consultation" where another uses "session" produces inconsistent documents that confuse the next agent and the human developer. The glossary is the single source of terminological truth.

## 2. Ubiquitous Language (DDD)

Eric Evans's principle in Domain-Driven Design: use **the same terms** in code, in documents, in conversations, and in the interface. When the domain model and the business language diverge, interpretation bugs arise.

**How to apply:**
- If the user says "prontuário" and the code says "medical_record", the glossary must define the canonical term and both sides must converge toward it.
- Never use generic terms ("item", "record", "thing") when there is a precise domain term.

## 3. Mandatory LGPD Terms (Art. 5, Law 13.709/2018)

For projects with health data or other sensitive personal data, these terms must appear in the glossary:

| Term | Legal Definition |
|-------|----------------|
| **Data Subject** | Natural person to whom the data refers |
| **Controller** | Who decides about the processing of data |
| **Processor** | Who carries out the processing on behalf of the controller |
| **DPO (Data Protection Officer)** | Person responsible for communication with data subjects and ANPD |
| **Personal data** | Info that identifies or makes a person identifiable |
| **Sensitive personal data** | Includes health, biometric, genetic, religious, political data |
| **Processing** | Any operation with personal data (collection, storage, use, etc.) |
| **Anonymization** | Process that makes it impossible to identify the data subject |
| **Pseudonymization** | Replacement of identifiers with pseudonyms (reversible) |
| **Consent** | Free, informed, and unambiguous expression of the data subject's will |

## 4. How to Identify Terms

### Event Storming (simplified)
List all **business events** of the system (e.g.: "Session scheduled", "Patient registered", "Payment completed"). Each noun is a candidate for a glossary term.

### Extraction from existing SPECs
Read the SPECs and extract nouns that appear more than 3 times. Each is a candidate.

### Questions to the user
- "What is the difference between X and Y?" (identifies terminological confusion)
- "What do you call this entity in day-to-day usage?" (identifies prohibited synonyms)

## 5. Pre-Save Checklist

- [ ] Every term has an operational definition (not just conceptual)
- [ ] Prohibited synonyms are listed for critical terms
- [ ] LGPD terms are documented (if the project involves personal data)
- [ ] No two terms have the same definition (duplicates removed)
- [ ] Deprecated terms point to their replacement
- [ ] The glossary was reviewed with the user to validate business terms

## 6. Example of Good vs Bad Entry

**Bad:**
```
### Session
- Definition: A session is a meeting between a psychologist and a patient.
```

**Good:**
```
### Session
- Definition: A scheduled and conducted meeting between a Psychologist and a Patient
  for clinical care. Has duration, date, status, and associated medical record.
- Context: Central unit of the system — all functionality revolves around the scheduling and recording of sessions.
- Do not confuse with: Consultation (general medical term, not used in this system), Meeting (administrative context).
- Prohibited synonyms: "consultation", "appointment", "encounter", "visit"
```
