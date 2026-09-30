# Role-Based Access Control (RBAC)

## 1. Overview

Role-Based Access Control (RBAC) is an authorization model in which access to resources is determined by the **roles assigned to a user** rather than by direct user-to-permission mappings. Instead of granting permissions to individual users, an administrator assigns permissions to named roles, and then assigns those roles to users. A user's effective permissions are the union of all permissions carried by their assigned roles.

The core idea is straightforward: people within an organization occupy positions — engineer, manager, auditor, support agent — and those positions naturally carry a predictable set of responsibilities. RBAC formalizes this intuition into an authorization model.

### What problem does RBAC solve?

In a naïve access control model, every permission is attached directly to a user record. When a company has hundreds of users, managing these individual mappings becomes expensive and error-prone. Granting a new employee access means locating and replicating every relevant permission. Revoking access on departure means hunting down every individual assignment. When policies change, every affected user record must be updated.

RBAC solves this by introducing an indirection layer — the **role** — so that permissions are managed once at the role level, and user management reduces to assigning or removing role memberships.

### What limitations of simpler models does RBAC address?

| Simpler model | Limitation addressed by RBAC |
|---|---|
| User-to-permission (ACL) lists | Too granular; scales poorly with team size |
| Hardcoded ownership checks | No reusability; code changes required for policy changes |
| Superuser / no-auth | No least-privilege; entire system is flat |

RBAC is the foundation that almost every larger authorization model builds upon or compares itself against. Understanding RBAC is a prerequisite for understanding ABAC, PBAC, and ReBAC.

---

## 2. Core Concepts

### 2.1 User (Subject)

A **user** is any entity that requests access to a resource. In practice this is a human account, a service account, or a machine identity. The authorization system only concerns itself with the identity of the subject after authentication has already confirmed who they are.

> **Authentication** establishes *who you are*. **Authorization** establishes *what you are allowed to do*. RBAC is purely an authorization concern.

**Example:** `alice@example.com` is a user in the system.

---

### 2.2 Role

A **role** is a named collection of permissions that represents a job function or organizational position. Roles are defined by administrators independent of individual users. A role has no meaning outside the set of permissions it carries and the users assigned to it.

**Example:** The `editor` role carries the permissions `articles:create`, `articles:update`, and `articles:read`.

---

### 2.3 Permission (Privilege)

A **permission** is an atomic statement of what action is allowed on what class of resource. Permissions are typically expressed as `resource:action` pairs or as named capability strings.

**Example:** `invoices:delete` is a permission that allows deleting invoices.

---

### 2.4 Role Assignment

A **role assignment** is the explicit relationship that connects a user to a role. It is a first-class data entity because it can carry additional metadata such as validity periods, scope constraints, or granting authority.

**Example:** Alice has been assigned the `editor` role. This means she inherits all permissions the `editor` role carries.

---

### 2.5 Role Hierarchy (optional)

Many RBAC implementations support **role hierarchies** where senior roles inherit all permissions of junior roles. This is sometimes called RBAC1 (the NIST RBAC model level 1).

**Example:** A `senior-editor` role inherits from `editor` and additionally carries `articles:publish`. Any user assigned `senior-editor` automatically also has `articles:create`, `articles:update`, and `articles:read`.

```
senior-editor
  └── editor
        ├── articles:create
        ├── articles:update
        └── articles:read
```

---

### 2.6 Separation of Duties (SoD) (optional)

Some RBAC implementations enforce **separation of duties** — a constraint that prevents the same user from holding two mutually exclusive roles simultaneously. This is sometimes called RBAC3.

**Example:** The `payment-initiator` and `payment-approver` roles are mutually exclusive. No single user may hold both roles at the same time, preventing unilateral payment authorization.

---

### 2.7 Session

A **session** is a runtime activation of a subset of an assigned role's permissions. A user with three roles may choose to activate only two of them for a particular session. Sessions are relevant in high-security environments but are rarely implemented in typical web applications.

---

## 3. How It Works

Authorization in RBAC follows a deterministic lookup process.

```mermaid
flowchart TD
    A([Incoming Request]) --> B[Authenticate user\nExtract user identity]
    B --> C[Look up role assignments\nfor this user]
    C --> D[Expand roles to\npermission sets]
    D --> E{Does the required\npermission exist\nin the expanded set?}
    E -- Yes --> F([✅ Allow])
    E -- No --> G([❌ Deny])
```

**Step-by-step:**

1. **Authenticate** — The system verifies the user's identity via a credential (JWT, session cookie, API key, etc.). RBAC begins after this step.
2. **Load role assignments** — The system retrieves which roles are assigned to this user from a data store or from claims inside a token.
3. **Expand permissions** — Each role is resolved to its permission set. If role hierarchies exist, parent role permissions are also included.
4. **Evaluate the required permission** — The action the user wants to perform on the resource is mapped to a required permission string (e.g., `invoices:delete`).
5. **Decision** — If the required permission is found in the user's effective permission set, access is allowed. Otherwise it is denied.
6. **Default-deny** — Any request that does not explicitly match an allowed permission is denied. There is no implicit allow.

---

## 4. Data Model

The following is a conceptual data model for a standard RBAC implementation. It is not tied to any specific database technology.

```
User
├── id: string
├── email: string
└── [other profile fields]

Role
├── id: string
├── name: string          -- e.g. "editor", "admin", "viewer"
├── description: string
└── parentRoleId: string? -- for role hierarchy (nullable)

Permission
├── id: string
├── resource: string      -- e.g. "articles", "invoices"
└── action: string        -- e.g. "create", "read", "update", "delete"

RolePermission             -- many-to-many: Role ↔ Permission
├── roleId: string
└── permissionId: string

UserRoleAssignment         -- many-to-many: User ↔ Role
├── userId: string
├── roleId: string
├── assignedAt: timestamp
├── expiresAt: timestamp?  -- optional time-bounded assignment
└── assignedBy: string     -- who granted this assignment (audit)
```

**Relationships summary:**

- A User can have many Roles (via UserRoleAssignment).
- A Role can have many Permissions (via RolePermission).
- A Role can optionally inherit from a parent Role.
- A User's effective permissions are the union of all permissions from all assigned roles (and their ancestors in a hierarchy).

---

## 5. Authorization Decision

### Inputs

| Input | Description |
|---|---|
| `userId` | The authenticated identity of the requester |
| `requiredPermission` | The permission needed for the requested action (e.g., `articles:delete`) |

### Evaluation Logic

```
effectivePermissions = ∅

for each roleAssignment where roleAssignment.userId == userId:
    role = loadRole(roleAssignment.roleId)
    effectivePermissions += role.permissions
    if role.parentRoleId exists:
        effectivePermissions += loadPermissionsRecursively(role.parentRoleId)

if requiredPermission ∈ effectivePermissions:
    return ALLOW
else:
    return DENY
```

### Allow condition

The required permission is present in the user's effective permission set.

### Deny condition

The required permission is absent from the user's effective permission set.

### Conflict handling

In standard RBAC there are no explicit deny rules. All permissions are positive grants. There is no concept of "deny this permission even if another role grants it." If any assigned role grants a permission, the user has it.

> This is an important limitation. Systems that need explicit denials must use ABAC or PBAC.

### Default behavior

**Default-deny.** A request is denied unless at least one assigned role explicitly grants the required permission.

### Policy precedence

Because all permissions are positive grants and there are no deny rules, precedence is not an issue in standard RBAC. The only question is whether the permission exists in any assigned role.

---

## 6. Practical Example

### Scenario: SaaS Content Management Platform

**Users:**

| User | Assigned Roles |
|---|---|
| Alice | `editor` |
| Bob | `viewer` |
| Carol | `admin` |
| Dave | `editor`, `billing-manager` |

**Roles and Permissions:**

| Role | Permissions |
|---|---|
| `viewer` | `articles:read` |
| `editor` | `articles:read`, `articles:create`, `articles:update` |
| `admin` | `articles:read`, `articles:create`, `articles:update`, `articles:delete`, `users:manage` |
| `billing-manager` | `invoices:read`, `invoices:export` |

**Resources:** Articles, Invoices, Users

---

**Allowed request:**

> Alice (`editor`) attempts to update an article.

Required permission: `articles:update`
Alice's roles: `editor` → permissions: `articles:read`, `articles:create`, `articles:update`
Decision: **ALLOW** — `articles:update` is in Alice's effective permission set.

---

**Denied request:**

> Bob (`viewer`) attempts to create an article.

Required permission: `articles:create`
Bob's roles: `viewer` → permissions: `articles:read`
Decision: **DENY** — `articles:create` is not in Bob's effective permission set.

---

**Cross-role permission:**

> Dave (`editor` + `billing-manager`) attempts to export an invoice.

Required permission: `invoices:export`
Dave's roles: `editor` + `billing-manager` → effective permissions: `articles:read`, `articles:create`, `articles:update`, `invoices:read`, `invoices:export`
Decision: **ALLOW** — `invoices:export` is present via the `billing-manager` role.

---

## 7. Implementation Example

The following is a framework-agnostic TypeScript implementation that demonstrates the actual authorization decision process.

```typescript
// --- Data types ---

interface Permission {
  resource: string;
  action: string;
}

interface Role {
  id: string;
  name: string;
  permissions: Permission[];
  parentRoleId?: string;
}

interface UserRoleAssignment {
  userId: string;
  roleId: string;
}

// --- Stores (in-memory for illustration) ---

const roles: Map<string, Role> = new Map([
  ["viewer",  { id: "viewer",  name: "viewer",  permissions: [{ resource: "articles", action: "read" }] }],
  ["editor",  { id: "editor",  name: "editor",  permissions: [
                  { resource: "articles", action: "read" },
                  { resource: "articles", action: "create" },
                  { resource: "articles", action: "update" },
                ], parentRoleId: undefined }],
  ["admin",   { id: "admin",   name: "admin",   permissions: [
                  { resource: "articles", action: "read" },
                  { resource: "articles", action: "create" },
                  { resource: "articles", action: "update" },
                  { resource: "articles", action: "delete" },
                  { resource: "users",    action: "manage" },
                ] }],
]);

const assignments: UserRoleAssignment[] = [
  { userId: "alice", roleId: "editor" },
  { userId: "bob",   roleId: "viewer" },
  { userId: "carol", roleId: "admin" },
];

// --- Authorization logic ---

function getEffectivePermissions(userId: string): Set<string> {
  const effective = new Set<string>();

  const userRoles = assignments
    .filter(a => a.userId === userId)
    .map(a => roles.get(a.roleId))
    .filter((r): r is Role => r !== undefined);

  for (const role of userRoles) {
    expandRole(role, effective);
  }

  return effective;
}

function expandRole(role: Role, accumulator: Set<string>): void {
  for (const perm of role.permissions) {
    accumulator.add(`${perm.resource}:${perm.action}`);
  }
  // Recurse into parent role if hierarchy is defined
  if (role.parentRoleId) {
    const parent = roles.get(role.parentRoleId);
    if (parent) {
      expandRole(parent, accumulator);
    }
  }
}

function isAuthorized(userId: string, resource: string, action: string): boolean {
  const required = `${resource}:${action}`;
  const effective = getEffectivePermissions(userId);
  return effective.has(required);
}

// --- Usage ---

console.log(isAuthorized("alice", "articles", "update")); // true
console.log(isAuthorized("bob",   "articles", "create")); // false
console.log(isAuthorized("carol", "users",    "manage")); // true
```

The decision function `isAuthorized` is the authorization boundary. It must be called at every protected operation, not just at login.

---

## 8. Advantages

### Security: Least-privilege by default

Users receive only the permissions their role requires. Adding a new user does not require touching permissions at all — only a role assignment is needed.

### Scalability: Role reuse

With thousands of users but a small number of distinct job functions, only the number of roles grows polynomially, not the user-permission mappings. A 5-role system with 10,000 users requires maintaining 5 permission sets, not 10,000.

### Maintainability: Centralized policy

Changing what an `editor` can do requires updating one role definition. All users assigned that role are affected immediately, without touching any user records.

### Auditability: Clear assignment trail

Every authorization decision traces back to: user → role assignment → role → permission. This chain is straightforward to audit. Compliance teams can answer "who has permission to delete invoices?" by querying which roles carry that permission and which users are assigned those roles.

### Onboarding and offboarding

New employees get access by role assignment. Departures are handled by removing role assignments. Neither operation requires touching permission definitions.

### Enterprise adoption

RBAC aligns naturally with HR systems, organizational hierarchies, and compliance frameworks such as SOC 2, ISO 27001, and HIPAA, which often mandate role-based access reviews.

---

## 9. Limitations and Trade-offs

### Coarse granularity

Standard RBAC grants permissions at the resource-class level, not at the resource-instance level. The `editor` role gives Alice permission to update *all* articles, not just the articles she authored. If the requirement is "editors can only update their own articles," RBAC alone cannot express this without either creating per-user roles (which defeats the purpose) or augmenting it with a different model.

### Role explosion

Real organizations have complex, overlapping permission requirements. Without discipline, the number of roles multiplies to handle every combination of slightly different permission sets. A system that starts with 10 roles can drift to hundreds. This is sometimes called **role explosion** and is one of the most common operational problems with RBAC in large enterprises.

### No context awareness

RBAC decisions are context-free. A permission is either granted or not, independent of time of day, IP address, data sensitivity, resource state, or any other contextual attribute. This is a fundamental design limitation, not an implementation problem.

### No instance-level control

RBAC cannot natively express "Alice can read documents in project A but not project B" without creating project-specific roles. Instance-level control requires FGAC, ABAC, or ReBAC.

### Static nature

RBAC reflects a static assignment. Dynamic access patterns — such as "grant access only during business hours" or "allow access only from the corporate network" — require additional layers beyond standard RBAC.

### Separation of duties enforcement

SoD constraints require additional infrastructure and discipline. Without it, users can accumulate conflicting roles over time, particularly in organizations without a robust identity governance process.

### Not appropriate for all trust models

RBAC assumes that all users with a given role are equivalent. This is not true in multi-tenant systems where a user's `admin` role in tenant A should not grant any access in tenant B. Tenant isolation must be designed explicitly.

---

## 10. When to Use It

RBAC is a strong fit when the following conditions hold:

- **Users map naturally to organizational roles.** If your user base has well-defined job functions with stable, shared permission sets, RBAC is the natural choice.
- **Permissions are at the resource-class level.** You want to control what type of resource a user can act on, not which specific instance.
- **The number of distinct permission profiles is small.** A few dozen roles serving thousands of users is the RBAC sweet spot.
- **Compliance requirements mandate role-based access reviews.** SOC 2, HIPAA, PCI-DSS, and ISO 27001 all reference role-based access in their controls.

**Realistic scenarios:**

| Scenario | Why RBAC fits |
|---|---|
| Internal admin dashboard | Clearly defined staff roles: `support`, `finance`, `engineering` |
| SaaS application with subscription tiers | Tiers map to roles: `free`, `pro`, `enterprise` |
| Enterprise ERP | HR-driven role assignments aligned to org chart |
| REST API with service accounts | Machine identities assigned roles: `read-only-service`, `data-pipeline` |
| Healthcare platform staff access | Regulatory roles: `clinician`, `billing`, `records-admin` |

---

## 11. When Not to Use It

RBAC is a poor fit — or insufficient on its own — in the following situations:

- **You need instance-level access control.** "A user can only edit their own posts" cannot be expressed in standard RBAC without role explosion. Use ReBAC or FGAC instead.
- **You need context-sensitive decisions.** "Allow access only from within the corporate VPN" or "deny access after business hours" requires attributes. Use ABAC or PBAC.
- **You have a highly dynamic permission model.** If permissions change based on resource state (e.g., a document in "draft" state has different access rules than one in "published" state), RBAC becomes unwieldy.
- **You have complex cross-tenant isolation requirements.** RBAC roles without explicit tenant scoping can lead to data leakage in multi-tenant architectures. ReBAC or ABAC with tenant attributes is more appropriate.
- **Your permission model is inherently relationship-based.** "Members of this team can access its repositories" is a relationship, not a role. ReBAC handles this more naturally.

---

## 12. Comparison With Other Authorization Models

| Model | Main Idea | Decision Inputs | Complexity | Best For |
|---|---|---|---|---|
| **RBAC** | Permissions assigned to roles; users assigned to roles | User's role memberships | Low–Medium | Organizations with clear job functions; compliance-driven systems |
| **FGAC** | Fine-grained control at the resource-instance level | User identity, specific resource, action | Medium | Multi-owner resources; row/cell-level data access |
| **ABAC** | Policies evaluated against subject, resource, action, and environment attributes | Attributes of user, resource, and context | High | Dynamic, context-sensitive access; large heterogeneous systems |
| **PBAC** | Centralized declarative policies evaluated at runtime | User identity, resource, action, context | High | Enterprise-wide unified policy enforcement; regulatory compliance |
| **ReBAC** | Access derived from graph relationships between entities | Graph relationships between user and resource | Medium–High | Social graphs; collaborative tools; hierarchical resource ownership |

No single model is universally superior. Many production systems combine RBAC with elements of ABAC or ReBAC to cover both coarse-grained organizational access and fine-grained resource-level control.

---

## 13. Security Considerations

### Privilege escalation

An attacker who can assign roles to themselves or others can gain unauthorized privileges. Role assignment must be treated as a high-privilege operation and protected behind its own authorization check (`roles:assign` permission or equivalent). Role assignment should also be logged immutably.

### Accumulation of excess permissions (permission creep)

Users who change job functions often retain their old role assignments in addition to gaining new ones. Over time this results in users holding far more permissions than their current position requires. Periodic access reviews (sometimes called re-certification campaigns) are essential to RBAC hygiene.

### Default-deny enforcement

The authorization check must be invoked on every protected operation. A common vulnerability is missing authorization checks on some endpoints, particularly internal or administrative ones. Every route, API endpoint, and data access point must require an explicit allow.

### Role definition integrity

Role definitions must be protected with the same rigor as the code they govern. An attacker who can modify role definitions can grant themselves arbitrary permissions without triggering a role assignment alert.

### Tenant isolation

In multi-tenant systems, role assignments must be scoped to a tenant. A user who is an `admin` in tenant A must not derive any access to tenant B's resources. Failing to include tenant scope in authorization checks is a common and serious vulnerability.

### Authorization caching

Caching role assignments or permission sets is a common performance optimization, but stale cache entries can allow access after a role is revoked. Use short TTLs and provide a mechanism to invalidate caches immediately on role or assignment changes.

### Audit logging

Every authorization decision — both allow and deny — should be logged with sufficient context to reconstruct the decision: user ID, role assignments at the time, required permission, resource, timestamp. This is essential for incident response and compliance audits.

### Administrative access bootstrap

The bootstrapping problem — who grants the first admin role — requires special care. Initial administrative access should be provisioned through infrastructure-level controls (environment variables, deployment scripts) rather than through the application itself, to avoid a circular dependency.

---

## 14. Performance Considerations

RBAC is one of the more performant authorization models because the decision path is a straightforward set membership check.

### Token-embedded claims

The most common performance optimization is embedding role assignments directly in the authentication token (e.g., JWT claims). This eliminates a database lookup on every request. The trade-off is that role changes take effect only after the token expires unless a token revocation mechanism is in place.

```json
{
  "sub": "alice",
  "roles": ["editor", "billing-manager"],
  "exp": 1700000000
}
```

### In-memory role cache

If roles are fetched from a database, they should be cached in memory (per process or in a shared cache such as Redis) with an appropriate TTL. Role definitions change infrequently, so long cache TTLs (minutes to hours) are usually acceptable.

### Permission expansion precomputation

For systems with deep role hierarchies, precomputing the flattened permission set for each role and caching it avoids recursive database queries at request time. This precomputed set can be invalidated and rebuilt whenever role definitions change.

### Avoid N+1 role lookups

A common performance mistake is loading role details inside a per-request loop. All roles for a user should be loaded in a single batched query, not one query per role assignment.

### Read-optimized data model

Role assignment lookups are a read-heavy, latency-sensitive path. A separate read-optimized table or document store (indexed by `userId`) can significantly reduce query time compared to joining across multiple normalized tables on every request.

---

## 15. Testing Strategy

A complete RBAC test suite must cover both the positive path (access granted) and the negative path (access denied), as well as boundary conditions and security constraints.

### Unit tests — role expansion

```
Test: Role permission expansion
Given: role "editor" with permissions ["articles:read", "articles:update"]
When:  getEffectivePermissions("alice") is called (alice is assigned "editor")
Then:  effective permissions include "articles:read" and "articles:update"
```

```
Test: Role hierarchy expansion
Given: role "senior-editor" inherits from "editor"
       "senior-editor" adds "articles:publish"
When:  getEffectivePermissions("dave") is called (dave is assigned "senior-editor")
Then:  effective permissions include "articles:read", "articles:update", "articles:publish"
```

### Unit tests — authorization decision

```
Test: Allowed action
Given: alice is assigned role "editor" which carries "articles:update"
When:  isAuthorized("alice", "articles", "update") is evaluated
Then:  result is ALLOW
```

```
Test: Denied action (permission absent)
Given: bob is assigned role "viewer" which carries only "articles:read"
When:  isAuthorized("bob", "articles", "create") is evaluated
Then:  result is DENY
```

```
Test: Default-deny with no roles
Given: charlie has no role assignments
When:  isAuthorized("charlie", "articles", "read") is evaluated
Then:  result is DENY
```

### Negative authorization tests

```
Test: Viewer cannot perform write operations
Given: user has role "viewer"
Then:  DENY for "articles:create", "articles:update", "articles:delete"
```

```
Test: Editor cannot manage users
Given: user has role "editor"
Then:  DENY for "users:manage"
```

### Privilege escalation tests

```
Test: Role assignment requires elevated permission
Given: alice has role "editor" (no "roles:assign" permission)
When:  alice attempts to assign the "admin" role to herself
Then:  request is DENY
```

```
Test: User cannot modify their own role assignments via the API
Given: bob makes a PATCH /users/bob/roles request
Then:  request is DENY unless bob holds "roles:assign"
```

### Multi-tenant isolation tests

```
Test: Role assignment is tenant-scoped
Given: alice is "admin" in tenant "acme-corp"
When:  alice requests a resource belonging to tenant "globex-corp"
Then:  result is DENY regardless of role
```

### Integration tests

```
Test: Revoked role takes effect immediately
Given: alice is assigned "editor"
When:  "editor" role is removed from alice
Then:  subsequent isAuthorized("alice", "articles", "update") returns DENY
       (validates that caches are invalidated correctly)
```

```
Test: Role update propagates to permission check
Given: "editor" role contains "articles:update"
When:  "articles:update" is removed from the "editor" role definition
Then:  alice (an "editor") can no longer update articles
```

---

## 16. Real-World Architecture

In a typical backend service, RBAC is evaluated after authentication and before business logic executes.

```mermaid
flowchart TD
    Client([Client]) -->|HTTP Request + Token| API[API Gateway\nor Load Balancer]
    API --> Auth[Authentication Layer\nValidates token\nExtracts user identity + role claims]
    Auth --> Authz[Authorization Layer\nRBAC check\nisAuthorized userId, resource, action]
    Authz -->|ALLOW| BL[Business Logic\nService Layer]
    Authz -->|DENY| Err([403 Forbidden])
    BL --> DB[(Database\nQuery scoped to allowed data)]
    BL --> Resp([Response])
```

### Where authorization should happen

**At the API boundary** — Every incoming request must pass an authorization check before any business logic runs. Performing authorization after data is fetched (i.e., loading a record and then checking if the user is allowed to see it) is a significant vulnerability because it relies on the developer never forgetting to add the check.

**Not inside the database** — Authorization logic should not live in SQL `WHERE` clauses as the primary enforcement point. Database-level filtering is a useful defense-in-depth measure, but the authoritative access decision must be made at the application layer.

**As middleware or decorators** — Implement RBAC checks as reusable middleware, decorators, or interceptors that are applied to routes declaratively, rather than writing `if (!isAuthorized(...)) return 403` manually in every handler. This reduces the risk of missing checks.

**Centralized policy store** — Role definitions and assignments should be stored in a central, authoritative location. Multiple services querying the same role store (or a local cache of it) ensures consistency across a distributed system.

### Token strategy

For stateless APIs, role claims are often embedded in JWTs:

```
Authorization: Bearer eyJhbGciOiJSUzI1NiJ9...
                          ↓
                     { "sub": "alice", "roles": ["editor"] }
```

This eliminates a round-trip to the role store on every request. The trade-off is that role changes are not reflected until the token is refreshed. For high-security systems, use short-lived tokens (5–15 minutes) combined with a token refresh mechanism.

---

## 17. Common Mistakes

### Mistake 1: Performing authorization only at login

**Problem:** The application checks roles during login and stores the result in a session or cookie. After login, no further authorization checks are performed.

**Why it is dangerous:** If a user's role is revoked after they log in, they retain access until their session expires. A session could last hours or days.

**Correct approach:** Evaluate `isAuthorized` on every protected request, not just once. If roles are embedded in a token, use short expiry times and validate that the token has not been revoked.

---

### Mistake 2: Building authorization into business logic ad hoc

**Problem:** Developers write inline checks throughout the codebase:
```typescript
// scattered across many files
if (user.role === "admin") { ... }
if (user.role === "editor" || user.role === "admin") { ... }
```

**Why it is dangerous:** These checks are inconsistent, hard to audit, and become maintenance nightmares. A policy change requires finding and updating every occurrence. Missed occurrences create privilege gaps.

**Correct approach:** Centralize authorization in a single `isAuthorized(userId, resource, action)` function. Apply it through middleware or decorators so it cannot be forgotten.

---

### Mistake 3: Omitting tenant scope from authorization checks

**Problem:** The check is `isAuthorized(userId, "invoices", "read")` without scoping to the tenant. In a multi-tenant system, this may allow a user from tenant A to read invoices from tenant B.

**Why it is dangerous:** This is a cross-tenant data leakage vulnerability, one of the most severe security issues in SaaS applications.

**Correct approach:** Always include the tenant context: `isAuthorized(userId, tenantId, "invoices", "read")`. The role assignment record must be scoped to a tenant so that roles in different tenants are completely independent.

---

### Mistake 4: Granting permissions at the wrong level of granularity

**Problem:** A single `admin` role is created with all permissions. When the product matures, some staff need "almost admin" access and the only option is to grant the full `admin` role.

**Why it is dangerous:** Over time, many users hold the `admin` role because it is the easiest way to grant the specific subset of permissions they need. Least-privilege is violated.

**Correct approach:** Design roles around job functions from the beginning. Prefer multiple focused roles over one catch-all role. Allow users to hold multiple roles simultaneously.

---

### Mistake 5: Treating role claims in a JWT as authoritative without validation

**Problem:** The API reads the `roles` array from a JWT payload and trusts it without verifying the token signature or expiry.

**Why it is dangerous:** Any client can craft a JWT with arbitrary role claims and gain unauthorized access.

**Correct approach:** Always verify the JWT signature against the issuer's public key before using any claim from the token. Reject tokens with invalid signatures or expired timestamps.

---

### Mistake 6: Ignoring role explosion

**Problem:** Every new edge case in permissions results in a new role. Over time the system accumulates hundreds of roles with subtle differences.

**Why it is dangerous:** The system becomes unmaintainable. Access reviews become unreliable because reviewers cannot meaningfully distinguish between 200 roles. Redundant roles carry duplicate permissions that diverge over time.

**Correct approach:** Before creating a new role, determine whether an existing role can be augmented or whether the use case requires a different model (ABAC or FGAC) rather than a new role.

---

## 18. Summary

**What it is:** Role-Based Access Control is an authorization model where permissions are grouped into named roles, and users are granted access by being assigned to those roles.

**How it works:** On each request, the system resolves the user's assigned roles to an effective permission set and checks whether the required permission for the requested action is present. Access is allowed if the permission is found; otherwise it is denied.

**Strengths:**
- Simple mental model that maps directly to organizational structure
- Scales well for systems with a manageable number of distinct permission profiles
- Easy to audit: the chain from user → role → permission is linear and traceable
- Strong alignment with regulatory compliance frameworks

**Limitations:**
- Cannot natively express instance-level or relationship-based access control
- Context-free: unable to incorporate environmental attributes into decisions
- Prone to role explosion in complex organizations
- Multi-tenant isolation requires explicit design discipline

**When to use it:** RBAC is the right starting point for most applications. It is best suited to systems where users belong to well-defined organizational roles with stable, shared permission requirements. For more complex authorization requirements — instance-level control, dynamic context, or relationship-driven access — RBAC should be augmented with or replaced by FGAC, ABAC, PBAC, or ReBAC.
