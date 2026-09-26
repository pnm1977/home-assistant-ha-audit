# HA Audit — User Guide

HA Audit is a read-only Home Assistant health and configuration auditing app.

It is designed to help you work through Home Assistant maintenance systematically:

**run → read → investigate → act → rerun**

HA Audit does not automatically repair or delete anything.

---

# 1. Running HA Audit

HA Audit currently runs manually.

In Home Assistant:

1. Go to **Settings → Apps**
2. Open **HA Audit**
3. Select **Start**
4. Wait for the app to finish
5. Open the **Log** tab

HA Audit stops automatically when the audit is complete.

A successful run ends with:

```text
HA Audit finished
