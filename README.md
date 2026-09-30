# Modern Authorization Systems

A production-quality reference for understanding and implementing modern authorization models.

This repository is aimed at software developers, software architects, and security engineers who need a technically accurate, framework-agnostic guide to the most widely used authorization models in production systems today.

---

## Authorization Models

| # | Model | Abbreviation | Core Idea | Best For |
|---|---|---|---|---|
| 01 | [Role-Based Access Control](docs/01_Role_Based_Access_Control.md) | RBAC | Permissions assigned to roles; users assigned to roles | Organizations with clear job functions; compliance-driven systems |
| 02 | [Fine-Grained Access Control](docs/02_Fine_Grained_Access_Control.md) | FGAC | Per-instance ACLs; explicit grants per subject and resource | Collaborative tools; ownership-driven sharing; per-resource access |
| 03 | [Attribute-Based Access Control](docs/03_Attribute_Based_Access_Control.md) | ABAC | Policies evaluated against attributes of subject, resource, and environment | Context-sensitive access; data classification; heterogeneous systems |
| 04 | [Policy-Based Access Control](docs/04_Policy_Based_Access_Control.md) | PBAC | Centralized declarative policies managed and deployed independently | Enterprise-wide consistent enforcement; regulatory compliance; multi-service architectures |
| 05 | [Relationship-Based Access Control](docs/05_Relational_Based_Access_Control.md) | ReBAC | Access derived from a graph of typed relationships between entities | Collaborative SaaS; hierarchical resources; team/org-based access |

---

## How to Read This Repository

Each document is self-contained and covers the same 18 sections:

1. Overview
2. Core Concepts
3. How It Works
4. Data Model
5. Authorization Decision
6. Practical Example
7. Implementation Example
8. Advantages
9. Limitations and Trade-offs
10. When to Use It
11. When Not to Use It
12. Comparison With Other Authorization Models
13. Security Considerations
14. Performance Considerations
15. Testing Strategy
16. Real-World Architecture
17. Common Mistakes
18. Summary

Start with the model most relevant to your current problem. Each document explains the model from first principles, so no prior knowledge of other models is required.

---

## Choosing a Model

There is no universally superior authorization model. The right model depends on the structure of your access requirements.

**Start here:**

```
Do users fall into a small number of job functions with shared permissions?
  → RBAC

Do users own specific resources and share them selectively?
  → FGAC (possibly layered on RBAC)

Does access depend on contextual attributes (time, location, data classification)?
  → ABAC

Must authorization policy be centrally governed and deployed independently of code?
  → PBAC

Is access derived from team membership, org hierarchy, or inter-resource relationships?
  → ReBAC
```

Most production systems combine two or more models. A typical architecture uses RBAC for coarse-grained feature access, FGAC or ReBAC for per-resource instance control, and ABAC or PBAC for context-sensitive or compliance-driven conditions.

---

## Key Distinctions

**Authentication vs. Authorization**
Authentication establishes *who you are*. Authorization establishes *what you are allowed to do*. All models in this repository are authorization models. They all begin after identity has been confirmed.

**Coarse-grained vs. Fine-grained**
RBAC operates at the resource-class level ("all articles"). FGAC, ReBAC, and ABAC can operate at the resource-instance level ("this specific article"). PBAC can operate at either level depending on how policies are written.

**Static vs. Dynamic decisions**
RBAC and FGAC produce the same decision for the same user and resource regardless of time or context. ABAC and PBAC can produce different decisions for the same user and resource depending on environmental attributes (time of day, network, resource state).

---

## AI-Generated Content Notice

> The documentation in this repository was generated with the assistance of an AI language model. AI can make mistakes — including technical inaccuracies, oversimplifications, or outdated information, particularly in security-sensitive domains. Always cross-reference with primary sources and have your authorization implementation reviewed by a qualified security engineer. See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) for details.

---

## Contributing

Please read our [Code of Conduct](CODE_OF_CONDUCT.md) before contributing. Corrections, improvements, and new authorization model documents are welcome.

---

## License

This documentation is released under the [MIT License](LICENSE).
