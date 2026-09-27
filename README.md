# IMIA — Industrial Maintenance Intelligence Agent

IMIA (Industrial Maintenance Intelligence Agent) is an AI-powered maintenance investigation assistant designed to help technicians investigate industrial equipment problems using technical documentation and maintenance history.

Instead of providing an unsupported AI-generated answer, IMIA retrieves relevant evidence from uploaded technical documents and connects that evidence to potential causes and recommended investigation steps.

> **Core idea: Show Me Why.**
>
> IMIA is designed to make AI-assisted maintenance investigations more transparent by showing the evidence behind an investigation.

---

## Overview

Industrial maintenance teams often need to investigate equipment failures using information spread across manuals, troubleshooting procedures, fault codes, and historical maintenance records.

IMIA brings these sources together into a single investigation workflow.

A technician can:

1. Upload a technical maintenance document.
2. Describe an equipment problem.
3. Run an AI-assisted investigation.
4. Review potential causes.
5. See why each cause may be relevant.
6. Inspect the evidence supporting each cause.
7. Review related maintenance history.
8. Follow recommended next investigation steps.

---

## Problem

Industrial equipment problems can require technicians to search through lengthy technical documentation while also considering previous failures and maintenance activity.

Traditional AI chat interfaces can produce plausible answers without clearly showing where the information came from.

IMIA focuses on an evidence-grounded investigation workflow where AI-generated reasoning is connected to retrieved source evidence.

---

## Solution

IMIA combines:

- Technical document processing
- Evidence retrieval
- Local AI reasoning
- Evidence validation
- Maintenance history
- Structured investigation results
- An interactive evidence viewer

The system retrieves relevant information from uploaded documentation and provides the AI model with that evidence when generating an investigation.

The backend then validates the evidence references returned by the AI before presenting them to the user.

---

## Key Features

### Evidence-Grounded Investigation

IMIA retrieves relevant sections of technical documentation before asking the AI model to investigate a problem.

Each retrieved section receives an evidence identifier such as:

```text
p1-c2
p2-c1
