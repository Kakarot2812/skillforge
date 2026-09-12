"""Cybersecurity Engineer roadmap definition with progressive practice problems."""
from typing import Any, Dict
from app.db.roadmaps_data.common import ROADMAP_IDS, make_problem, make_skill

CYBERSECURITY_ROADMAP: Dict[str, Any] = {
    "id": ROADMAP_IDS["cybersecurity-engineer"],
    "slug": "cybersecurity-engineer",
    "role_id": None,
    "title": "Cybersecurity Engineer",
    "domain": "Cybersecurity",
    "category": "Security & Infrastructure",
    "description": "Defend enterprise systems and applications against modern adversaries: network protocols, Linux hardening, applied cryptography, web vulnerability exploitation/mitigation (OWASP Top 10), identity governance, SIEM threat hunting, and cloud security architecture.",
    "version": "v2.0",
    "has_market_data": False,
    "stages": [
        {
            "order": 1,
            "name": "Stage 1 — Security Fundamentals & Operating Systems",
            "description": "Deep network packet analysis, OSI model security, and enterprise Linux operating system defense.",
            "skills": [
                make_skill(
                    slug="networking-security",
                    name="Computer Networking & Protocols for Security",
                    canonical_slug=None,
                    difficulty="BEGINNER",
                    description="Network security foundations: TCP/IP stack, DNS, ARP, DHCP, packet inspection with Wireshark/tcpdump, routing security, firewalls, and port scanning.",
                    key_topics=["TCP/IP Model & Protocol Vulnerabilities", "Packet Sniffing & Analysis (Wireshark, tcpdump)", "DNS Architecture, DNSSEC & Spoofing", "Firewall Fundamentals (iptables, nftables)", "Port Scanning & Network Enumeration (Nmap)"],
                    role_relevance="The foundation of all network defense, intrusion detection, and perimeter boundary enforcement.",
                    prerequisites=[],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "Wireshark User's Guide", "url": "https://www.wireshark.org/docs/wsug_html_chunked/", "description": "Official guide to capturing, filtering, and dissecting network packet traces."},
                        {"type": "YOUTUBE", "title": "CompTIA Network+ Full Course — Professor Messer", "url": "https://www.youtube.com/watch?v=0k5iZl48s_A", "description": "In-depth tutorial covering TCP/IP, subnets, routing protocols, and network troubleshooting."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="net-sec-prob-1",
                            title="Packet Capture & Handshake Dissection",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Capture and analyze a TCP 3-way handshake and DNS resolution query using Wireshark / tcpdump.",
                            problem_statement="Using tcpdump or Wireshark, capture network traffic during an HTTPS browsing session. Identify and document the SYN, SYN-ACK, ACK packet sequence, window sizing, sequence numbers, and the preceding DNS A/AAAA query and response records.",
                            requirements=[
                                "Capture packets filtered by host and port using BPF (Berkeley Packet Filters).",
                                "Identify relative vs absolute TCP sequence numbers.",
                                "Analyze DNS transaction IDs and flags (recursion desired vs available).",
                                "Produce a concise technical report explaining the handshake state transitions."
                            ],
                            concepts_tested=["TCP 3-Way Handshake", "Wireshark Display Filters", "Berkeley Packet Filters (BPF)", "DNS Protocol Mechanics"],
                            expected_outcome="A packet analysis report detailing protocol headers and state transitions.",
                            optional_hints=["Use display filter 'tcp.flags.syn == 1' to isolate connection initiation packets."]
                        ),
                        make_problem(
                            problem_id="net-sec-prob-2",
                            title="Nmap Port Enumeration & Vulnerability Scripting",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Perform thorough, stealthy network reconnaissance and banner grabbing using Nmap and NSE scripts.",
                            problem_statement="Scan a simulated target subnet. Differentiate between SYN stealth scans (-sS) and full connect scans (-sT). Execute OS fingerprinting, service version detection (-sV), and run specific Nmap Scripting Engine (NSE) vulnerability checks (vuln, default) while avoiding firewall rate-limiting.",
                            requirements=[
                                "Compare packet signatures of SYN stealth scan vs TCP connect scan.",
                                "Tune timing templates (-T2 vs -T4) to avoid triggering intrusion alerts.",
                                "Execute targeted NSE scripts (e.g. ssl-enum-ciphers, http-headers).",
                                "Output findings in structured XML and greppable formats."
                            ],
                            concepts_tested=["Nmap Scan Techniques", "NSE Scripting Engine", "Stealth Reconnaissance", "Service Fingerprinting"],
                            expected_outcome="A structured network inventory identifying open ports, service versions, and potential CVEs.",
                            optional_hints=["SYN scans (-sS) send a RST packet upon receiving SYN-ACK, never completing the full TCP connection."]
                        ),
                        make_problem(
                            problem_id="net-sec-prob-3",
                            title="Stateful Firewall Configuration with Nftables",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Build a production stateful network firewall with nftables enforcing default-drop policies and rate limiting.",
                            problem_statement="Design an nftables firewall configuration for an edge server. Enforce default DROP for incoming and forwarded traffic, permit established/related connections via conntrack, allow SSH with connection rate limiting (max 3 connections per minute per IP to prevent brute force), and log dropped packets with prefix tags.",
                            requirements=[
                                "Define inet filter table with input, forward, and output chains.",
                                "Enforce default drop policy on input and forward chains.",
                                "Allow stateful traffic: ct state established,related accept.",
                                "Implement dynamic set with meter for SSH rate-limiting (limit rate over 3/minute drop).",
                                "Configure rate-limited kernel logging for dropped packets."
                            ],
                            concepts_tested=["Stateful Firewall Rules", "Nftables Syntax & Chains", "Conntrack State Inspection", "Anti-Brute Force Rate Limiting"],
                            expected_outcome="A hardened, test-validated firewall configuration blocking unauthorized ingress traffic.",
                            optional_hints=["Nftables replaced iptables as the modern Linux packet filtering framework."]
                        ),
                    ],
                ),
                make_skill(
                    slug="linux-security",
                    name="Linux Operating System Security & Administration",
                    canonical_slug=None,
                    difficulty="BEGINNER",
                    description="Hardening Linux environments: file permissions, sudoers least privilege, SSH key-based authentication, PAM modules, auditd auditing, and mandatory access control (SELinux/AppArmor).",
                    key_topics=["Linux Permissions (rwx, SUID, SGID, Sticky Bit)", "Sudoers Configuration & Least Privilege", "Hardened SSH Configuration (sshd_config)", "System Auditing with auditd", "Mandatory Access Control (SELinux / AppArmor)"],
                    role_relevance="The dominant server operating system; properly securing Linux is mandatory for cloud infrastructure resilience.",
                    prerequisites=[],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "CIS Linux Benchmarks", "url": "https://www.cisecurity.org/benchmark/ubuntu_linux", "description": "Authoritative industry benchmark for hardening Linux distributions and server configurations."},
                        {"type": "YOUTUBE", "title": "Linux Security & Hardening Crash Course — NetworkChuck", "url": "https://www.youtube.com/watch?v=0k5iZl48s_A", "description": "Hands-on guide to SSH hardening, UFW, fail2ban, and permissions audits."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="lin-sec-prob-1",
                            title="File Permission Audit & SUID Binary Hunting",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Identify dangerous file permissions, misconfigured world-writable directories, and unwanted SUID/SGID binaries.",
                            problem_statement="Write a bash script audit_permissions.sh that scans a Linux system for files with SUID/SGID bits set, finds world-writable files and directories lacking the sticky bit, and checks for improper ownership on /etc/passwd and /etc/shadow.",
                            requirements=[
                                "Use find / -perm -4000 to discover SUID executables.",
                                "Verify /etc/shadow is owned by root:shadow with mode 0640 or 0600.",
                                "Locate world-writable directories lacking the sticky bit (+t).",
                                "Generate a remediation script that revokes unnecessary elevated permissions."
                            ],
                            concepts_tested=["Linux File Permissions", "SUID / SGID Bit Auditing", "Sticky Bit Security", "Automated Bash Auditing"],
                            expected_outcome="A thorough permission audit report and automated remediation script.",
                            optional_hints=["SUID allows an executable to run with the privileges of the file owner (often root)."]
                        ),
                        make_problem(
                            problem_id="lin-sec-prob-2",
                            title="Production SSH Hardening & Fail2ban Integration",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Harden the OpenSSH daemon against unauthorized access and configure Fail2ban automated jail bans.",
                            problem_statement="Configure /etc/ssh/sshd_config to disable root login, disable password authentication, enforce Ed25519 public key authentication, restrict allowed ciphers and MACs to modern cryptographic standards, and deploy Fail2ban to ban IPs after 3 failed authentication attempts.",
                            requirements=[
                                "Set PermitRootLogin no and PasswordAuthentication no.",
                                "Configure modern KexAlgorithms (curve25519-sha256) and Ciphers (chacha20-poly1305, aes256-gcm).",
                                "Create a Fail2ban jail.local configuration with bantime=1h and maxretry=3.",
                                "Test the configuration using ssh -T and simulate failed logins to verify iptables/nftables ban execution."
                            ],
                            concepts_tested=["SSH Daemon Hardening", "Cryptographic Cipher Suites", "Fail2ban Automated Defense", "Log Parsing & Banning"],
                            expected_outcome="An impenetrable SSH service completely immune to password brute-force attacks.",
                            optional_hints=["Always test SSH configuration changes in a secondary session before terminating your active connection."]
                        ),
                        make_problem(
                            problem_id="lin-sec-prob-3",
                            title="Kernel Security Auditing with Auditd & SELinux Enforcement",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Configure Linux Audit Daemon (auditd) rules for compliance monitoring and enforce SELinux confinement on web daemons.",
                            problem_statement="Create an auditd rule suite (/etc/audit/rules.d/compliance.rules) monitoring all file modifications to critical system files (/etc/pam.d, /etc/sudoers) and tracking execution of privileged system calls (execve). Additionally, configure SELinux in Enforcing mode and resolve confinement denials using audit2why and custom policy modules.",
                            requirements=[
                                "Write auditd watch rules with custom keys (-k sudo_actions, -k system_mod).",
                                "Query audit logs using ausearch and generate summary reports with aureport.",
                                "Ensure SELinux is set to Enforcing mode (getenforce).",
                                "Diagnose an AVC denial using audit2why and generate a confined policy module using audit2allow."
                            ],
                            concepts_tested=["Auditd Kernel Auditing", "SELinux Mandatory Access Control", "AVC Denial Diagnosis", "System Call Tracking"],
                            expected_outcome="An auditable operating system environment logging all privileged actions and enforcing MAC containment.",
                            optional_hints=["audit2allow -M mypolicy creates compiled .pp policy packages from AVC denial logs."]
                        ),
                    ],
                ),
            ],
        },
        {
            "order": 2,
            "name": "Stage 2 — Cryptography & Application Defense",
            "description": "Mathematical security foundations, PKI infrastructure, and OWASP Top 10 web vulnerability remediation.",
            "skills": [
                make_skill(
                    slug="crypto-pki",
                    name="Applied Cryptography & PKI Fundamentals",
                    canonical_slug=None,
                    difficulty="INTERMEDIATE",
                    description="Cryptographic primitives and infrastructure: symmetric encryption (AES-GCM), asymmetric encryption (RSA, ECC), cryptographic hashing (SHA-256, Argon2), digital signatures, certificates, and Public Key Infrastructure (PKI).",
                    key_topics=["Symmetric vs Asymmetric Cryptography", "Authenticated Encryption (AES-256-GCM, ChaCha20-Poly1305)", "Secure Password Hashing (Argon2id, bcrypt)", "X.509 Digital Certificates & CA Chains", "TLS 1.3 Handshake & Forward Secrecy"],
                    role_relevance="Guarantees data confidentiality, integrity, and authenticity across untrusted networks and storage mediums.",
                    prerequisites=["networking-security"],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "OpenSSL Official Documentation", "url": "https://www.openssl.org/docs/", "description": "Official guides to cryptography commands, certificate management, and TLS protocols."},
                        {"type": "YOUTUBE", "title": "Cryptography Full Course — freeCodeCamp", "url": "https://www.youtube.com/watch?v=2aHkqB2-46k", "description": "Comprehensive course covering ciphers, public key cryptography, digital signatures, and hash functions."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="crypt-prob-1",
                            title="Authenticated Encryption & Argon2 Password Vault",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Implement secure password-based file encryption using Argon2id key derivation and AES-GCM-256.",
                            problem_statement="Write a Python utility using the cryptography library that takes a master passphrase, derives a 256-bit encryption key using Argon2id with salt, encrypts a sensitive file using AES-GCM (generating a fresh random 12-byte nonce), and validates data integrity upon decryption.",
                            requirements=[
                                "Derive cryptographic keys using argon2-cffi or cryptography Argon2id.",
                                "Encrypt data using AESGCM with a cryptographically secure random nonce (os.urandom(12)).",
                                "Prepend salt and nonce to the ciphertext payload.",
                                "Verify that tampering with a single bit of ciphertext throws an InvalidTag authentication error."
                            ],
                            concepts_tested=["Argon2id Key Derivation", "AES-GCM Authenticated Encryption", "Nonce Uniqueness", "Integrity Tag Verification"],
                            expected_outcome="A tamper-evident encryption tool providing authenticated confidentiality.",
                            optional_hints=["Never reuse an AES-GCM nonce with the same key; it completely destroys cryptographic confidentiality."]
                        ),
                        make_problem(
                            problem_id="crypt-prob-2",
                            title="Private PKI Certificate Authority Architecture",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Build a complete private two-tier Public Key Infrastructure (Root CA + Intermediate CA) using OpenSSL.",
                            problem_statement="Construct a private PKI hierarchy. Generate a 4096-bit RSA Root Certificate Authority with a 10-year validity, create an Intermediate CA signed by the Root, issue end-entity TLS server certificates with Subject Alternative Names (SANs), and verify the certificate chain using openssl verify.",
                            requirements=[
                                "Create custom OpenSSL configuration files (openssl.cnf) enforcing basicConstraints and keyUsage extensions.",
                                "Sign Intermediate CA with Root CA and securely store the Root private key.",
                                "Generate end-entity certificates containing valid DNS Subject Alternative Names (SANs).",
                                "Validate full chain of trust: openssl verify -CAfile root.crt -untrusted intermediate.crt server.crt."
                            ],
                            concepts_tested=["Two-Tier PKI Architecture", "Certificate Signing Requests (CSR)", "X.509 v3 Extensions & SAN", "Chain of Trust Verification"],
                            expected_outcome="A functional enterprise private Certificate Authority capable of issuing trusted internal certificates.",
                            optional_hints=["Modern browsers reject TLS certificates lacking Subject Alternative Name (SAN) extensions."]
                        ),
                        make_problem(
                            problem_id="crypt-prob-3",
                            title="TLS 1.3 Handshake & Perfect Forward Secrecy Audit",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Audit a server's TLS configuration for Perfect Forward Secrecy (PFS), cipher suites, and protocol vulnerabilities.",
                            problem_statement="Use testssl.sh or sslyze to evaluate a public or staging TLS server. Identify weak ciphers (CBC mode, 3DES, RC4), confirm TLS 1.2/1.3 enforcement with Ephemeral Diffie-Hellman (ECDHE) key exchange, verify OCSP Stapling and HSTS headers, and formulate a remediation plan.",
                            requirements=[
                                "Execute an automated scan identifying insecure SSLv3, TLS 1.0, and TLS 1.1 protocols.",
                                "Verify that all negotiated cipher suites provide Perfect Forward Secrecy (PFS).",
                                "Configure Nginx / Apache to achieve an A+ rating on Qualys SSL Labs benchmark.",
                                "Implement HTTP Strict Transport Security (HSTS) with includeSubDomains and preload directives."
                            ],
                            concepts_tested=["TLS 1.3 Protocol Security", "Perfect Forward Secrecy (PFS / ECDHE)", "Cipher Suite Hardening", "HSTS Header Configuration"],
                            expected_outcome="A certified A+ TLS server configuration immune to downgrade and decryption attacks.",
                            optional_hints=["Perfect Forward Secrecy ensures past session keys cannot be decrypted even if the server private key is leaked in the future."]
                        ),
                    ],
                ),
                make_skill(
                    slug="web-app-security",
                    name="Web Application Security & OWASP Top 10",
                    canonical_slug=None,
                    difficulty="INTERMEDIATE",
                    description="Defending web applications against critical vulnerabilities: SQL Injection, Cross-Site Scripting (XSS), CSRF, Broken Object Level Authorization (BOLA), SSRF, and Security Headers.",
                    key_topics=["OWASP Top 10 Vulnerabilities Overview", "SQL Injection (SQLi) & Parameterized Queries", "Cross-Site Scripting (Reflected, Stored, DOM XSS)", "Server-Side Request Forgery (SSRF) Prevention", "Content Security Policy (CSP) & Defense Headers"],
                    role_relevance="The frontline of application security, protecting enterprise APIs and web portals against direct adversary exploitation.",
                    prerequisites=["networking-security", "linux-security"],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "OWASP Top Ten Web Application Security Risks", "url": "https://owasp.org/www-project-top-ten/", "description": "Official OWASP documentation for the most critical web security vulnerabilities and mitigations."},
                        {"type": "YOUTUBE", "title": "OWASP Top 10 Explained — freeCodeCamp", "url": "https://www.youtube.com/watch?v=0k5iZl48s_A", "description": "Detailed walkthrough explaining each OWASP vulnerability with practical attack and defense examples."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="web-sec-prob-1",
                            title="SQL Injection Exploit & Parameterized Remediation",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Exploit a classic SQL injection vulnerability in a test lab and remediate it using parameterized prepared statements.",
                            problem_statement="In a vulnerable web app lab, execute an authentication bypass using SQL injection (' OR '1'='1), extract database schema information via UNION-based injection, and then rewrite the underlying backend code to use parameterized queries eliminating the flaw completely.",
                            requirements=[
                                "Demonstrate authentication bypass on a vulnerable login endpoint.",
                                "Extract table names using UNION SELECT table_name FROM information_schema.tables.",
                                "Refactor backend code to use parameterized queries / ORM prepared statements.",
                                "Verify automated payloads fail harmlessly with parameterized execution."
                            ],
                            concepts_tested=["SQL Injection Exploitation", "UNION-Based Data Extraction", "Parameterized Prepared Statements", "Input Sanitization"],
                            expected_outcome="A patched application with zero vulnerability to SQL injection.",
                            optional_hints=["Parameterized queries separate the query structure from untrusted user data at the database parser level."]
                        ),
                        make_problem(
                            problem_id="web-sec-prob-2",
                            title="Stored XSS Remediation & Content Security Policy (CSP)",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Remediate stored Cross-Site Scripting vulnerabilities via contextual output encoding and a strict Content Security Policy.",
                            problem_statement="Given a commenting feature where user input executes arbitrary JavaScript (<script>alert(document.cookie)</script>), implement context-aware HTML entity encoding on output and configure a strict Content Security Policy (CSP) header that disallows inline scripts and restricts script origins.",
                            requirements=[
                                "Demonstrate how unescaped user comments execute malicious JavaScript in victim browsers.",
                                "Implement contextual HTML escaping (htmlspecialchars / DOMPurify) before browser rendering.",
                                "Construct an HTTP response header with Content-Security-Policy: default-src 'self'; script-src 'self'.",
                                "Verify that attempted inline script injections are actively blocked by the browser CSP engine."
                            ],
                            concepts_tested=["Stored XSS Prevention", "Contextual Output Encoding", "Content Security Policy (CSP)", "Browser Execution Policies"],
                            expected_outcome="A hardened web page protected by defense-in-depth output encoding and browser CSP rules.",
                            optional_hints=["Never rely on input blacklists to prevent XSS; use strict output encoding and CSP."]
                        ),
                        make_problem(
                            problem_id="web-sec-prob-3",
                            title="SSRF Exploitation & Cloud Metadata Protection",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Simulate and block a Server-Side Request Forgery (SSRF) attack targeting cloud instance metadata endpoints.",
                            problem_statement="A web application accepts a URL parameter to fetch remote avatars. An attacker submits http://169.254.169.254/latest/meta-data/iam/security-credentials to steal cloud IAM keys. Remediate this vulnerability by implementing strict URL scheme allowlists, IP address resolution validation, and blocking all private RFC 1918 / link-local addresses.",
                            requirements=[
                                "Demonstrate how the vulnerable endpoint requests internal network addresses.",
                                "Implement DNS resolution pre-check: resolve hostname to IP and reject loopback (127.0.0.1), private (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16), and link-local (169.254.169.254) ranges.",
                                "Protect against DNS rebinding: ensure the HTTP request connects directly to the validated IP address.",
                                "Validate that cloud metadata queries return an immediate 400 Bad Request error."
                            ],
                            concepts_tested=["Server-Side Request Forgery (SSRF)", "Cloud Metadata Service Protection", "DNS Rebinding Defense", "IP Range Validation"],
                            expected_outcome="An HTTP fetcher service impervious to SSRF and cloud credential harvesting.",
                            optional_hints=["Disable HTTP redirects in your client or re-validate resolved IPs on every redirected hop."]
                        ),
                    ],
                ),
            ],
        },
        {
            "order": 3,
            "name": "Stage 3 — Identity, Vulnerability & Penetration Testing",
            "description": "IAM architectures, credential security, automated vulnerability scanning, and offensive penetration methodologies.",
            "skills": [
                make_skill(
                    slug="iam-security",
                    name="Identity, Authentication & Access Management",
                    canonical_slug=None,
                    difficulty="INTERMEDIATE",
                    description="Identity and access architecture: OAuth 2.0, OpenID Connect (OIDC), SAML 2.0, Multi-Factor Authentication (MFA / FIDO2 / WebAuthn), Role-Based & Attribute-Based Access Control (RBAC/ABAC), and session security.",
                    key_topics=["OAuth 2.0 Authorization Framework (Grant Types, PKCE)", "OpenID Connect (OIDC) & JWT Claims Validation", "Multi-Factor Authentication (TOTP, FIDO2/WebAuthn)", "Role-Based (RBAC) & Attribute-Based (ABAC) Access Control", "Session Management & Secure Cookie Attributes"],
                    role_relevance="The perimeter has shifted to identity; robust IAM is the primary gatekeeper for enterprise data assets.",
                    prerequisites=["networking-security"],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "OAuth 2.0 and OpenID Connect — Auth0 Docs", "url": "https://auth0.com/docs/authenticate/protocols/oauth", "description": "Official guides to authorization code flow, PKCE, token validation, and scopes."},
                        {"type": "YOUTUBE", "title": "OAuth 2.0 and OpenID Connect Explained — Okta", "url": "https://www.youtube.com/watch?v=996OiexHze0", "description": "Clear conceptual animation explaining difference between authorization and authentication."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="iam-prob-1",
                            title="JWT Security & Signature Verification Engine",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Implement cryptographically secure JSON Web Token (JWT) validation and prevent common signature bypass flaws.",
                            problem_statement="Write an authentication middleware that validates JWT tokens. Verify the signature against RS256 public keys, check expiration (exp) and issuer (iss) claims, reject the insecure 'none' algorithm, and extract user identity claims safely.",
                            requirements=[
                                "Explicitly whitelist allowed signing algorithms (algorithms=['RS256']) to prevent 'alg: none' attacks.",
                                "Validate exp, nbf, and iss claims with strict clock skew tolerance.",
                                "Handle token expiration gracefully with clear 401 Unauthorized error messages.",
                                "Write unit tests attempting token tampering, expired tokens, and invalid signatures."
                            ],
                            concepts_tested=["JWT Structure (Header, Payload, Signature)", "Signature Verification", "Algorithm Confusion Defense", "Token Claims Validation"],
                            expected_outcome="A robust JWT verification middleware resistant to token forgery exploits.",
                            optional_hints=["Never trust the 'alg' header from incoming tokens without validating against an allowed list on the server."]
                        ),
                        make_problem(
                            problem_id="iam-prob-2",
                            title="OAuth 2.0 Authorization Code Flow with PKCE",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Implement OAuth 2.0 Authorization Code Flow with Proof Key for Code Exchange (PKCE) for a single-page app.",
                            problem_statement="Build an OAuth 2.0 client integration using PKCE. Generate a cryptographically random code_verifier, compute code_challenge = base64url(sha256(code_verifier)), initiate authorization redirect, exchange authorization code along with code_verifier for tokens, and validate received ID tokens.",
                            requirements=[
                                "Generate high-entropy code_verifier string (43-128 characters).",
                                "Compute SHA-256 code_challenge with code_challenge_method='S256'.",
                                "Exchange authorization code for access and ID tokens.",
                                "Verify that authorization server rejects token requests if code_verifier does not match challenge."
                            ],
                            concepts_tested=["OAuth 2.0 Authorization Code Flow", "PKCE (Proof Key for Code Exchange)", "Authorization vs Authentication", "Token Exchange Security"],
                            expected_outcome="A secure authentication flow that protects against authorization code interception attacks.",
                            optional_hints=["PKCE is mandatory for all public clients (SPAs, mobile apps) that cannot safely store a client secret."]
                        ),
                        make_problem(
                            problem_id="iam-prob-3",
                            title="Fine-Grained ABAC Policy Enforcement Engine",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Design and implement an Attribute-Based Access Control (ABAC) engine evaluating complex contextual authorization rules.",
                            problem_statement="Develop an ABAC authorization engine (using Open Policy Agent / Rego or Python). Evaluate requests against policies taking into account: subject attributes (department, clearance), resource attributes (confidentiality tier, owner), action (read, write), and environmental attributes (time of day, network origin IP, device compliance status).",
                            requirements=[
                                "Define declarative policy rules in Rego or JSON/Python.",
                                "Enforce conditional rules (e.g. 'Confidential documents can only be accessed during work hours from corporate IP range').",
                                "Return clear decision reasons (Allow, Deny with violated conditions).",
                                "Benchmark evaluation latency to ensure sub-5ms decision times for high-volume API gateways."
                            ],
                            concepts_tested=["Attribute-Based Access Control (ABAC)", "Contextual Authorization Rules", "Policy Enforcement Point (PEP)", "Low-Latency Policy Evaluation"],
                            expected_outcome="A zero-trust contextual authorization engine capable of enterprise policy enforcement.",
                            optional_hints=["Open Policy Agent (OPA) evaluates declarative Rego policies decoupled from application code."]
                        ),
                    ],
                ),
                make_skill(
                    slug="vuln-pentest",
                    name="Vulnerability Assessment, Scanning & Penetration Testing",
                    canonical_slug=None,
                    difficulty="ADVANCED",
                    description="Offensive security and vulnerability management: vulnerability scanners (Nessus, OpenVAS), web proxies (Burp Suite, OWASP ZAP), exploit frameworks (Metasploit), CVSS scoring, and penetration testing methodologies.",
                    key_topics=["Vulnerability Assessment Lifecycle & Scanning", "Web Application Proxies (Burp Suite, ZAP)", "Exploitation Concepts & Metasploit Framework", "CVSS v3.1 / v4.0 Vulnerability Scoring", "Penetration Testing Execution Standard (PTES)"],
                    role_relevance="Enables security engineers to think like an adversary and discover critical flaws before malicious threat actors do.",
                    prerequisites=["web-app-security", "linux-security"],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "PortSwigger Web Security Academy", "url": "https://portswigger.net/web-security", "description": "Free, authoritative interactive labs and tutorials for web application penetration testing."},
                        {"type": "YOUTUBE", "title": "Ethical Hacking Course — freeCodeCamp", "url": "https://www.youtube.com/watch?v=fNzpcB7ODxQ", "description": "Hands-on guide to reconnaissance, port scanning, exploitation frameworks, and vulnerability analysis."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="pen-prob-1",
                            title="Burp Suite Interception & Parameter Tampering",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Intercept and manipulate HTTP requests using Burp Suite Proxy and Repeater to bypass client-side checks.",
                            problem_statement="Configure a web browser to route traffic through Burp Suite. Intercept an e-commerce checkout request, tamper with client-side price parameters ($100.00 -> $0.01), inspect server response, and document how client-side validation without server enforcement leads to business logic flaws.",
                            requirements=[
                                "Install Burp Suite CA certificate in browser certificate store.",
                                "Intercept and inspect HTTP POST request parameters in Burp Proxy.",
                                "Send request to Burp Repeater and modify hidden form field values.",
                                "Document the business logic vulnerability and specify server-side price lookup remediation."
                            ],
                            concepts_tested=["HTTP Interception Proxies", "Client-Side Parameter Tampering", "Burp Repeater", "Business Logic Vulnerabilities"],
                            expected_outcome="A vulnerability findings report explaining why client-side controls cannot be trusted.",
                            optional_hints=["Always calculate transaction prices server-side from database records, never from client form fields."]
                        ),
                        make_problem(
                            problem_id="pen-prob-2",
                            title="Automated Vulnerability Scanning & CVSS Prioritization",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Execute an automated vulnerability scan using OpenVAS / Nuclei and prioritize remediation using CVSS scoring.",
                            problem_statement="Run an automated vulnerability scan against a target staging environment using Nuclei or OpenVAS. Filter false positives, evaluate confirmed findings, calculate CVSS v3.1 vector strings, and produce an executive summary prioritizing fixes based on exploitability and business impact.",
                            requirements=[
                                "Execute targeted Nuclei templates for known CVEs and exposed panels.",
                                "Analyze scan findings and eliminate false positives through manual verification.",
                                "Calculate CVSS v3.1 base and temporal scores for confirmed vulnerabilities.",
                                "Generate a remediation roadmap ranking vulnerabilities into Critical, High, Medium, and Low."
                            ],
                            concepts_tested=["Vulnerability Scanning (Nuclei)", "CVSS v3.1 Vector Scoring", "False Positive Verification", "Remediation Prioritization"],
                            expected_outcome="An actionable vulnerability assessment report ready for engineering remediation sprints.",
                            optional_hints=["CVSS vector strings encapsulate Attack Vector, Complexity, Privileges Required, User Interaction, and Scope."]
                        ),
                        make_problem(
                            problem_id="pen-prob-3",
                            title="End-to-End Penetration Test & Privilege Escalation",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Conduct an ethical penetration test on an authorized vulnerable target machine from initial access to root privilege escalation.",
                            problem_statement="In a dedicated virtual lab (e.g. Hack The Box / VulnHub machine), perform initial reconnaissance, identify an unpatched web service vulnerability to obtain a low-privilege reverse shell, enumerate local privilege escalation vectors (misconfigured sudo or cron job), escalate to root, and write a formal penetration testing report adhering to PTES.",
                            requirements=[
                                "Identify vulnerable service during port scanning and service enumeration.",
                                "Deploy a stable reverse shell connection using netcat / python pty.",
                                "Run privilege escalation audit tools (LinPEAS) and identify misconfiguration.",
                                "Escalate privileges to root and capture proof flags.",
                                "Write a formal Penetration Testing Report including Executive Summary, Technical Narrative, and Remediation Steps."
                            ],
                            concepts_tested=["Penetration Testing Methodology (PTES)", "Reverse Shell Stability", "Linux Privilege Escalation", "Professional Pentest Reporting"],
                            expected_outcome="A professional, comprehensive penetration testing report outlining attack paths and defensive fixes.",
                            optional_hints=["LinPEAS automates checking hundreds of Linux privilege escalation vectors in minutes."]
                        ),
                    ],
                ),
            ],
        },
        {
            "order": 4,
            "name": "Stage 4 — Operations, Threat Hunting & Cloud Defense",
            "description": "Security operations, log analysis with SIEM, incident response handling, and cloud security posture hardening.",
            "skills": [
                make_skill(
                    slug="soc-incident-response",
                    name="Security Operations, SIEM & Incident Response",
                    canonical_slug=None,
                    difficulty="INTERMEDIATE",
                    description="Detection engineering and incident handling: SIEM platforms (Splunk, Elastic SIEM), log aggregation, threat hunting, IOC detection, Sigma rules, and NIST/SANS incident response lifecycles.",
                    key_topics=["SIEM Architecture & Log Ingestion", "Detection Engineering with Sigma Rules", "Indicators of Compromise (IOCs) & Threat Intelligence", "NIST Incident Response Lifecycle (Preparation, Detection, Containment, Eradication, Recovery)", "Digital Forensics & Memory Artifact Analysis"],
                    role_relevance="The operational command center that detects active intrusions, contains breaches, and restores business operations.",
                    prerequisites=["networking-security", "linux-security"],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "NIST Computer Security Incident Handling Guide (SP 800-61)", "url": "https://csrc.nist.gov/publications/detail/sp/800-61/rev-2/final", "description": "Authoritative standard for structuring enterprise incident response teams and handling processes."},
                        {"type": "YOUTUBE", "title": "SOC Analyst Training Course — freeCodeCamp", "url": "https://www.youtube.com/watch?v=0k5iZl48s_A", "description": "Practical walkthrough of SIEM dashboards, alert triage, log searching, and malware analysis."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="soc-prob-1",
                            title="SIEM Log Analysis & Brute-Force Detection Query",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Write SIEM detection queries in Splunk SPL or Elasticsearch KQL to detect distributed password spraying attacks.",
                            problem_statement="Given raw authentication logs from Linux servers (/var/log/auth.log) or Active Directory Event ID 4625, construct a SIEM correlation search that flags any single source IP generating more than 10 failed login attempts across multiple distinct usernames within a 5-minute rolling window.",
                            requirements=[
                                "Write query in Splunk SPL (stats count dc(user) by src_ip) or Elastic KQL.",
                                "Filter for failed authentication event types.",
                                "Group by source IP and set threshold: count > 10 AND dc(username) > 3.",
                                "Trigger an automated alert payload formatting source IP, target users, and timestamps."
                            ],
                            concepts_tested=["SIEM Log Querying (SPL/KQL)", "Correlation Search Rules", "Password Spraying Detection", "Event Aggregation"],
                            expected_outcome="An operational SIEM detection rule accurately alerting on password spraying attacks.",
                            optional_hints=["Distinct count of usernames (dc(user)) differentiates password spraying from a single locked-out user."]
                        ),
                        make_problem(
                            problem_id="soc-prob-2",
                            title="Sigma Detection Rule & Threat Hunting",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Author a generic Sigma detection rule targeting adversary command-and-control activity and convert it to target SIEM queries.",
                            problem_statement="Write a Sigma rule (threat_hunting_c2.yml) that detects suspicious PowerShell execution flags (-enc, -nop, -w hidden) associated with Cobalt Strike or Empire stagers. Convert the Sigma rule using sigma-cli into native Splunk SPL, Elastic KQL, and Microsoft Sentinel KQL queries.",
                            requirements=[
                                "Structure the Sigma rule with metadata: title, status, description, author, references, and MITRE ATT&CK tags (T1059.001).",
                                "Define detection logic matching process creation events and command line arguments.",
                                "Convert the rule to at least two target SIEM backends using sigma-cli.",
                                "Test queries against simulated telemetry to verify alert firing."
                            ],
                            concepts_tested=["Sigma Rule Development", "MITRE ATT&CK Mapping", "Cross-Platform Detection Engineering", "PowerShell Threat Hunting"],
                            expected_outcome="A portable Sigma detection rule deployed across enterprise SIEM query engines.",
                            optional_hints=["Sigma rules decouple detection logic from specific proprietary SIEM query dialects."]
                        ),
                        make_problem(
                            problem_id="soc-prob-3",
                            title="Ransomware Incident Containment & Forensic Timeline",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Execute an incident response playbook to contain a simulated ransomware infection and construct a forensic timeline.",
                            problem_statement="A workstation is reported displaying a ransom note. Follow the NIST SP 800-61 lifecycle: execute immediate network isolation, preserve volatile memory artifacts using LiME / DumpIt, analyze master file table ($MFT) and prefetch files to identify the patient-zero execution timestamp, locate persistence mechanisms (scheduled tasks, registry run keys), and produce an Incident Response Post-Mortem.",
                            requirements=[
                                "Document immediate containment actions (host isolation without rebooting).",
                                "Extract volatile memory dump and inspect running processes.",
                                "Build a chronological forensic timeline identifying the initial access vector.",
                                "Produce an Incident Response Post-Mortem detailing root cause, indicators of compromise (IOCs), and corrective preventive controls."
                            ],
                            concepts_tested=["NIST Incident Response Lifecycle", "Network Containment Strategies", "Forensic Timeline Reconstruction", "Incident Post-Mortem Reporting"],
                            expected_outcome="A completed forensic analysis and post-mortem report documenting the incident response.",
                            optional_hints=["Never power off an infected machine immediately; powering off destroys invaluable RAM artifacts."]
                        ),
                    ],
                ),
                make_skill(
                    slug="cloud-security-hardening",
                    name="Cloud Security & Infrastructure Hardening",
                    canonical_slug=None,
                    difficulty="ADVANCED",
                    description="Securing multi-tenant cloud environments: AWS/Azure security best practices, CloudTrail auditing, GuardDuty threat detection, Infrastructure-as-Code security scanning (Checkov, tfsec), and zero-trust workload identity.",
                    key_topics=["Cloud Shared Responsibility Model", "Cloud Infrastructure Entitlement Management (CIEM)", "Cloud Security Posture Management (CSPM)", "Static Code Analysis for IaC (Checkov, tfsec)", "Container & Kubernetes Security Fundamentals"],
                    role_relevance="Critical for safeguarding cloud-native microservices, serverless workloads, and enterprise cloud data lakes.",
                    prerequisites=["linux-security", "iam-security"],
                    resources=[
                        {"type": "DOCUMENTATION", "title": "AWS Security Best Practices Whitepaper", "url": "https://docs.aws.amazon.com/whitepapers/latest/aws-security-best-practices/welcome.html", "description": "Official AWS guidance for account isolation, identity federation, data encryption, and monitoring."},
                        {"type": "YOUTUBE", "title": "AWS Cloud Security Full Course — freeCodeCamp", "url": "https://www.youtube.com/watch?v=0k5iZl48s_A", "description": "Hands-on walkthrough of AWS IAM, KMS, VPC security groups, GuardDuty, and compliance auditing."},
                    ],
                    practice_problems=[
                        make_problem(
                            problem_id="csec-prob-1",
                            title="IaC Security Scanning with Checkov in CI/CD",
                            difficulty="BEGINNER",
                            order=1,
                            objective="Scan Terraform infrastructure code for security misconfigurations and enforce automated CI/CD quality gates.",
                            problem_statement="Integrate Checkov into a GitHub Actions CI/CD workflow. Scan Terraform code defining S3 buckets and security groups, flag misconfigurations (public read S3 buckets, open 0.0.0.0/0 SSH security groups, missing encryption), and fail the build if high-severity violations are found.",
                            requirements=[
                                "Run checkov -d terraform/ in local environment.",
                                "Identify and remediate at least 3 critical security findings (e.g. CKV_AWS_20, CKV_AWS_24).",
                                "Configure a GitHub Actions step running checkov --framework terraform --soft-fail=false.",
                                "Demonstrate that introducing a public S3 bucket breaks the CI pipeline."
                            ],
                            concepts_tested=["Infrastructure-as-Code (IaC) Security", "Checkov Static Analysis", "CI/CD Security Gates", "Cloud Misconfiguration Prevention"],
                            expected_outcome="An automated CI security check preventing insecure cloud infrastructure from being deployed.",
                            optional_hints=["Shifting security left into Terraform scans prevents misconfigurations from ever reaching production cloud APIs."]
                        ),
                        make_problem(
                            problem_id="csec-prob-2",
                            title="CloudTrail Threat Detection & GuardDuty Responder",
                            difficulty="INTERMEDIATE",
                            order=2,
                            objective="Automate real-time security response to unauthorized cloud API calls using AWS EventBridge and Lambda.",
                            problem_statement="Deploy an automated security responder. When AWS GuardDuty detects unauthorized API activity or root account console login in CloudTrail, trigger an EventBridge rule that invokes a serverless Lambda function to revoke compromised IAM session tokens and send an urgent alert to the security Slack channel.",
                            requirements=[
                                "Configure CloudTrail to log all management and data events to an encrypted S3 bucket.",
                                "Create an EventBridge rule matching GuardDuty finding type 'UnauthorizedAccess:IAMUser/ConsoleLoginSuccess'.",
                                "Implement a Python Lambda function calling iam:RevokeSecurityToken to terminate active sessions.",
                                "Test response by simulating an unauthorized login event."
                            ],
                            concepts_tested=["CloudTrail Audit Ingestion", "GuardDuty Threat Findings", "EventBridge Real-Time Triggers", "Automated Remediation with Lambda"],
                            expected_outcome="A self-defending cloud account that revokes compromised sessions within seconds of detection.",
                            optional_hints=["EventBridge matches JSON event patterns from GuardDuty and triggers Lambda functions with near-zero latency."]
                        ),
                        make_problem(
                            problem_id="csec-prob-3",
                            title="Zero-Trust Kubernetes Workload Confinement",
                            difficulty="ADVANCED",
                            order=3,
                            objective="Harden Kubernetes container workloads using security contexts, NetworkPolicies, and Admission Controllers.",
                            problem_statement="Secure a production Kubernetes cluster namespace hosting a microservice. Enforce Pod Security Standards (Restricted profile), configure read-only root filesystems and non-root UID execution in securityContext, write default-deny Kubernetes NetworkPolicies allowing only required microservice egress, and audit admission with Kyverno or OPA Gatekeeper.",
                            requirements=[
                                "Configure pod securityContext: runAsNonRoot: true, readOnlyRootFilesystem: true, allowPrivilegeEscalation: false, drop: [ALL].",
                                "Deploy a default-deny ingress/egress NetworkPolicy for the namespace.",
                                "Allow specific ingress from an API gateway pod on port 8080 only.",
                                "Verify that attempting to deploy a privileged pod is actively rejected by the Kubernetes admission webhook."
                            ],
                            concepts_tested=["Kubernetes Pod Security Standards", "NetworkPolicy Micro-Segmentation", "Container Security Contexts", "Admission Webhook Enforcement"],
                            expected_outcome="A confined zero-trust Kubernetes environment preventing container breakout and lateral movement.",
                            optional_hints=["A read-only root filesystem prevents attackers from dropping binaries or scripts inside a compromised container."]
                        ),
                    ],
                ),
            ],
        },
    ],
}
