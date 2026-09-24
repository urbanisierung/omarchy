# Project review and next steps

This directory records the September 24, 2026 review of this opinionated,
Fedora-based Hyprland desktop and tracks implementation of the resulting plan.

| Document | Purpose |
| --- | --- |
| [Installation audit](installation-audit.md) | Findings, evidence, severity, and verification limits |
| [Action plan](action-plan.md) | Ordered implementation tasks and acceptance criteria |
| [Naming proposals](naming-proposals.md) | Five possible identities and naming tradeoffs |
| [Kickstart USB](kickstart-usb.md) | Guided test-media building, VM gate, flashing and recovery |

**Current assessment:** the installer is not yet a dependable way to reproduce
the configured desktop on a fresh Fedora system. Passing shell syntax checks and
focused regression tests does not establish fresh-install readiness.

The first bootstrap/early-failure safety batch is implemented, with 36 passing
tests. See [implementation progress](action-plan.md#implementation-progress) for
the exact scope and remaining limitations. Live desktop configuration is unchanged.

Guided Fedora 44 USB assets and an ISO builder are now implemented separately
from the desktop stages. ISO creation, VM boot, and physical installation remain
unverified; follow the [USB guide](kickstart-usb.md) rather than treating this as
an unattended disk-wiping installer.

Start with the decisions in [Phase 0](action-plan.md#phase-0-agree-on-the-supported-installation).
Then repair bootstrap and desktop provisioning before expanding features.
No project rename has been selected or implemented.

## Relationship to existing documents

- [PLAN.md](../PLAN.md) is an upstream feature-adoption proposal. It is not an
  installation readiness checklist; its feature work should follow this repair plan.
- [FEDORA_CONVERSION_SUMMARY.md](../FEDORA_CONVERSION_SUMMARY.md) is historical
  context, not proof that today's package lists and scripts work on fresh Fedora.
- [Translation notes](../hyprtranslate-docs.md) and
  [dictation notes](../hyprwhspr-docs.md) describe manual setup that needs to be
  reconciled with the automated installer.

The project can retain its opinionated defaults without tracking upstream
Omarchy feature-for-feature. The goal is a reproducible personal workstation,
not a general-purpose distribution installer.
