---
id: GLOSSARY-v1
title: "Domain Glossary — {PROJECT_NAME}"
status: Active # Deprecated
version: 1.0
created: YYYY-MM-DD
updated: YYYY-MM-DD
---

# Domain Glossary — {PROJECT_NAME}

Status: 🟢 Active  
Updated: YYYY-MM-DD

> **Usage:** Every agent and developer must consult this glossary before creating documents. Always use the **Canonical Term**. Never use Prohibited Synonyms.

---

## Business Domain

### {Term}

- **Definition:** {precise operational definition — what this term means in the context of this system}
- **Context:** {when and where this term is used}
- **Do not confuse with:** {similar terms with distinct meanings}
- **Prohibited synonyms:** {terms that MUST NOT be used as substitutes}

---

## Technical

### {Term}

- **Definition:** {precise technical definition}
- **Context:** {system layer where this concept appears — e.g.: API, database, UI}
- **Do not confuse with:** {similar terms}
- **Prohibited synonyms:** {none | list}

---

## LGPD

> Definitions based on Art. 5 of Law 13.709/2018.

### Personal Data

- **Definition:** Information related to an identified or identifiable natural person.
- **Context:** Any data that allows identifying a user of the system (name, CPF, email, phone).
- **Do not confuse with:** Anonymized data (which does not allow identification).
- **Prohibited synonyms:** "user data" (imprecise), "personal information"

### Sensitive Personal Data

- **Definition:** Personal data about racial or ethnic origin, religious belief, political opinion, trade union membership, health or sexual life data, genetic or biometric data.
- **Context:** Patients' mental health data falls into this category — requires explicit consent.
- **Do not confuse with:** Common personal data.
- **Prohibited synonyms:** "sensitive data" (use the full term)

### Data Subject

- **Definition:** The natural person to whom the personal data being processed refers.
- **Context:** In the system: the patient whose health data is stored.
- **Prohibited synonyms:** "data owner", "user"

### Controller

- **Definition:** The natural or legal person who makes decisions regarding the processing of personal data.
- **Context:** The clinic or professional responsible for the system.
- **Prohibited synonyms:** "data responsible"

### Processor

- **Definition:** The natural or legal person who processes personal data on behalf of the controller.
- **Context:** The software system and its AI agents that process patient data.
- **Prohibited synonyms:** "operator"

### Processing

- **Definition:** Any operation performed with personal data: collection, production, reception, classification, use, access, reproduction, transmission, distribution, processing, archiving, storage, deletion, evaluation or control of information, modification, communication, transfer, diffusion or extraction.
- **Context:** Any operation in the system that involves patient data constitutes processing.
- **Prohibited synonyms:** "data use", "data processing"

---

## Infra

### {Term}

- **Definition:** {infrastructure component definition}
- **Context:** {where this component runs and what it is for}
- **Prohibited synonyms:** {none | list}

---

## Deprecated

| Old Term | Replaced by | Since |
|----------|------------|-------|
| {old term} | {canonical term} | YYYY-MM-DD |

---

## References

- LGPD: Art. 5, Law 13.709/2018
- Glossary updated on: YYYY-MM-DD
