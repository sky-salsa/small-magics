---
name: hand-down
version: 1.3
description: Save project state for the next agent. Trigger on /hand-down, "handdown", "hand down", "save state", "wrap up", or before /clear or /compact.
---

# /hand-down — Continuity Handoff

> **Note on former names.** This skill was previously named `/handoff`, and its partner `/hand-up` was previously `/handon`. Mentions of `/handoff` or `/handon` in a repo's own documents are almost always references to those former names — you are allowed and encouraged to update them to `/hand-down` and `/hand-up` whenever you encounter them. Do not confuse this with the separate `/handoff` skill that may appear in your skills list: that is an unrelated skill by a different author, not an earlier version of this one.

When this skill triggers, your job is one thing: **make sure the next agent dropped into this project with zero context can pick up exactly where things left off.**

You do this by ensuring four things exist:

1. An **index file** that maps the project's docs and assets so the next agent finds everything fast
2. A **state file** — where things stand, what's next, what to read first, what not to break
3. A **learning log** — accumulated lessons, conventions, decisions, and issues
4. A **CLAUDE.md pointer line** — guarantees the next agent finds the state file

These files together form the project's handoff state. The user is asking for this because they're about to end the session, clear context, compact, or otherwise hand off — they want to preserve context / state for whoever picks up next.

### State Files Organization Standard

Follow this organization standard if creating new state files or new scoped workstream state files. 
If state files already created in a different structure, mention to user it may be worth re-organizing at some point for consistency. 

Every workstream — including the project-wide one — gets its own directory under a single `workstreams/` folder at the **project root**. Each of those holds a `state/` subfolder containing that workstream's three handoff files, sitting alongside whatever working files the workstream owns.

```
<project-root>/
├── CLAUDE.md                       ← pointer ONLY. Stays at root. Not a state file.
├── workstreams/
│   ├── Main/                       ← the project-wide workstream (default target)
│   │   └── state/
│   │       ├── startup.md          ← where things stand, what's next, read-first
│   │       ├── _index.md           ← one line per doc/asset
│   │       └── learning-log.md     ← lessons + decisions, newest first
│   ├── <workstream-slug>/          ← scoped mode: one dir per workstream
│   │   ├── state/
│   │   │   ├── startup.md
│   │   │   ├── _index.md
│   │   │   └── learning-log.md
│   │   └── …                       ← that workstream's own working files
│   └── <workstream-slug>/
│       └── state/                  ← same three files, always
└── …                               ← shared project files: source, docs, assets
```

Rules this encodes:

- **Same three filenames everywhere.** `startup.md`, `_index.md`, `learning-log.md`. An agent that learns the shape once can navigate any project.
- **`Main/` is just the macro default workstream.** Non-scoped runs write to `workstreams/Main/state/`. Scoped runs write to their own workstream and leave `Main/` alone.
- **Workstream dirs are siblings, never nested.** No workstream owns another.
- **Slugs are short and match the workstream label**: Same label used in CLAUDE.md or AGENTS.md used in the `### Scoped workstreams` pointer list, so an agent maps label → directory without guessing.

## Skill log

This skill keeps its own issue log at `service files/skill log/`: one short markdown file per problem noticed with how `/hand-down` or `/hand-up` behaves. If you hit a real issue with what the skill is supposed to do (now, or mid-hand-up), or if Sky says "add this to the skill log," drop a dated file there (`YYYY-MM-DD-slug.md`), noting whether it was a hand-down or hand-up issue. That is the whole ritual. This is separate from the project learning log in Operation 2.

## Trust your context

You already have the session's context. You already see what files exist when you Read or Glob the project. You don't need a detection algorithm to find these files — you can recognize them when you see them. Look around, use the existing context, and trust your judgment.

The reason this matters: this skill is meant to be lightweight. Heavy file-scanning logic adds nothing — by the time you're invoking the skill, you usually already know whether the project has a state file. If you don't know, take one quick pass with Glob or Read.

---

## Optional Scoped mode (subdirectory handoff)

By default, the operations below write to **`workstreams/Main/state/`**: one shared handoff for the whole directory. Use **scoped mode** instead when the user asks for it. Signals: "scoped handoff," "let's do a scoped /hand-down," "/hand-down scoped," "scope this to a subdirectory," "don't overwrite the main handoff," or any explicit request for a scoped or subdir handoff.

**Ignore this if user does not indicate that scoped mode is being used for this handoff. If uncertain, ask.** 

In scoped mode, everything works the same with three differences:

1. **Pick a workstream name and a subdirectory.** Derive a short slug from what this session is actually working on (confirm with the user if it is not obvious). Write the state file, learning log, and index into `workstreams/<slug>/state/` instead of `workstreams/Main/state/`.
2. **Don't rewrite Main's handoff files.** Your handoff lives in your own workstream directory. You can read Main's state docs if they help your subtask, but in this mode you are not updating or rehashing them. Don't worry much about what is in Main unless you judge it necessary.
3. **Use a labeled pointer instead of the plain one.** In place of Operation 3's plain pointer, add or update your workstream's line in a `### Scoped workstreams` list in the root `CLAUDE.md`. Leave any existing main-project pointer line and any other workstream's line untouched. Add, never replace.

Labeled pointer format (sits alongside any existing main pointer, does not replace it):

```
### Scoped workstreams
Pick up the one matching your task. If you are not sure which is yours, ask before reading.
- **<Workstream name>** → `workstreams/<slug>/state/startup.md`
```

The workstream name is the identity. A returning agent matches its task to the label (and `/hand-up` will ask the user when the match is unclear), which is how the next agent knows which handoff is for it.

---

## Operation 1: Index file (every run, unconditional)

**This is not optional, and it is the operation most likely to get silently dropped. Run it every time the skill fires:** create the index if none exists, update it if one does, the same way the CLAUDE.md pointer in Operation 3 runs unconditionally. 

**What is the index?:** The index is an organized list of documents meant to help you and other agents avoid consuming any information that is not necessary until the moment it is needed. It is your primary tool for organizing yourself and your project;s documents in an atomic way. Each document created during the project should serve a specific purpose and be registered accordingly in the index in such a way that an agent with no context, would understand what purpose it serves and what it contains. Any document that needs to be accessed repeatedly should be kept short with any unnecessary or legacy data being moved to archive type documents. 

The index is the map a zero-context agent reads first. It scans the index, finds the pages that matter in that moment, and opens only those. Without a current index, the next agent reconstructs the project blind, which is the exact cost this skill exists to prevent.

The pattern this skill borrows from (Karpathy's LLM-wiki) works for one reason: the index is refreshed every time anything is added, because the moment it goes stale the navigation silently breaks. So treat updating the index as the most important piece of ongoing maintenance through the session. 

The index is the most important document in the state file set of documents because it is the tool that gives you and other agents vision and the ability to understand the shape of a project and your environment without having to guess from scratch. 

**Definition.** The index is a single, scannable markdown file that catalogs the project's documents and assets, one line each, so a fresh agent reads ONE file and knows what exists, where it is, and what it is for. It is not a retrieval system and not RAG: no embeddings, no chunking, just a human-readable table of contents that lets the agent open fewer whole files as the library grows.

**Scope it to the work at hand.** Catalog the documents and assets tied to the current project and this handoff (plans, designs, references, notes, the handoff files, important directories), not source code, which git (and if needed Graphify) already make navigable. "Catalog everything" means every handoff-relevant doc, not every file in the tree, and never files belonging to other workstreams or projects sharing the directory. Keep the whole index readable in one pass. 

Common names: `_index.md`, `index.md`. Recognize it when you see it.

### Entry format

One line per item: a backticked path, then a colon and a short "what it is, when to read it", plus a light tag in brackets. Group entries under short headings.

```
## Start here
- `startup.md`: current state, focus, next steps. [state]
- `learning-log.md`: accumulated lessons and decisions, newest first. [log]

## Working docs
- `plans/phase-2.md`: plan for the scheduler rework. [plan]

## Reference / assets
- `references/api-notes.md`: Directus API quirks. [reference]
- `assets/brand/`: logo and color tokens for this client. [asset]
```

### If an index exists

Update it: add newly-created docs and assets, remove deleted ones, fix one-liners that are now wrong. Leave accurate lines alone.

### If no index exists

Create `_index.md` in `workstreams/Main/state/` from `templates/index.md` (in this skill's directory), populated from what you can see in context. Then point the state file's **Files to Read First** at it, so the entry chain reads: CLAUDE.md, then the state file, then the index, then everything else.

Keep the index lightweight: catalog what's relevant, do not be exhaustive, and never let it sprawl past a single readable pass. But "lightweight" never means "skipped." If the session genuinely changed nothing catalog-worthy, still confirm the index exists and is current, and say so in the end-of-run summary, so the check is visible instead of silent.

---

## Operation 2: State file

**Definition.** A state file is the file in this project that tells a fresh agent where things stand right now, what to do next, what files to read first, and what NOT to break or change without understanding first.

Common names: `startup.md`, `state.md`, `handoff.md`, `project_status.md` ,`Start here`. You don't need a list — you can recognize one when you see one. **Important note:** Claude.md is NOT a state file and should not be treated as such.

### If a state file exists

Update it. Specifically:
- Refresh **Current Focus** with the active topic of work as of this session
- Update **What's Next** with the next items in the active queue
- Move newly-finished work into **Recently Completed** (cap that section at ~10 bullets — prune oldest as you add new; this is a rolling window, not an infinite log)
- Update load-bearing items in **Critical Context** if anything changed
- Update the file paths in **Files to Read First** if the relevant set has changed
- Update the `last_updated` field in frontmatter to current `YYYY-MM-DD HH:MM TZ`

Don't rewrite sections that didn't change in this session. Don't editorialize. Reflect what actually happened.

### If no state file exists

Create `startup.md` in `workstreams/Main/state/` using the template at `templates/startup.md` (in this skill's directory).

Fill in:
- Frontmatter: `project` name, `created` and `last_updated` set to current `YYYY-MM-DD HH:MM TZ`
- **Start Here** — direct, explicit instructions to the next agent ("Read X first. The current thread is Y. Pick up by doing Z.") 2-4 sentences max
- **Project Description** — 1-3 sentences on what this project is
- **Core Design Stance** *(optional)* — only if the project has a foundational principle worth surfacing; otherwise delete the section entirely
- **Recently Completed** — bullet list of recently finished work (cap ~10)
- **Current Focus** — top-line topic of active work right now (1-3 bullets or short paragraph)
- **What's Next** — next items in the active queue (~5-7 max)
- **Critical Context** — load-bearing items where understanding is necessary but not sufficient before changing them
- **Files to Read First** — curated list with one-line "why" each

After populating, delete the `<!-- DELETE AFTER POPULATING -->` instruction comments from the template.

---

## Operation 3: Learning log

**Definition.** A learning log is the file where accumulated project lessons, conventions, decisions, and issues live for future agents to reference. Chronological, prepend-only. Reference, not active tracker. User will sometimes refer to this as an error log when requesting additions to this file. 

Common names: `learning-log.md`, `learnings.md`, `lessons.md`, `conventions.md`,`error log.md`. Recognize it when you see it. Could also be a directory with multiple individual entries.

### Entry format

Every entry uses this format:

```
### YYYY-MM-DD HH:MM TZ
**[origination-tag]** content
```

Where origination tag is one of:

- **`[user-requested]`** — the user explicitly asked for this entry to be logged. Either to learning log or to error log. Content is **verbatim** the user's words, with **only minor grammar cleanup**. No paraphrasing. No "the user said" preamble. No editorialization. Preserves user voice and intent exactly.
- **`[agent]`** — you observed something worth logging on your own initiative. Content is your own framing — write what you noticed, decided, or learned. you are encouraged to take notes here on things learned. 

### If a learning log exists

**Prepend** new entries from this session worth logging. Insert directly below the blockquote header at the top, **above** any existing entries. Newest first.

Examples of what's worth logging:
- A convention adopted during this session ("we agreed all timestamps include time")
- A decision made and the reasoning ("decided to use prepend over append because...")
- An issue discovered ("noticed the X hook fires inconsistently")
- A lesson learned ("realized Y pattern doesn't work because...")

What's NOT worth logging: routine task progress (that's the state file), general session activity, things easily inferable from code or git.

**Do not edit existing entries.** Ever. Prepend only.

If the user explicitly asks for something to be logged ("log this: we decided to..."), use `[user-requested]` and quote them verbatim with only grammar cleanup.

### If no learning log exists

Create `learning-log.md` in `workstreams/Main/state/` using the template at `templates/learning-log.md` (in this skill's directory).

If there's nothing worth logging from this session, still create the file with the template — but leave the body empty. Future sessions will populate it.

---

## Operation 4: CLAUDE.md pointer (every run, unconditional)

This is the retention mechanism. CLAUDE.md is reliably read by agents on fresh starts and post-compact starts. A single pointer line is what guarantees the next agent finds the state file.

**Run this every time the skill fires, regardless of what happened in operations 1 and 2.**

### Logic

- **If `CLAUDE.md` exists in the project root:**
  - Check whether it already contains a pointer line that references the state file
  - If yes → do nothing, you're done
  - If no → add a single pointer line near the top of the file (after any title/heading, before other content)

- **If `CLAUDE.md` does not exist:**
  - Create `CLAUDE.md` in the project root with just the pointer line

### Pointer line format

```
Read `<state-file-path>` in full first — it has current project state, focus, and what to read next.
```

Replace `<state-file-path>` with the actual path (e.g., `workstreams/Main/state/startup.md`).

Keep it to one line. The whole point is lightweight retention. If the user wants more in CLAUDE.md, that's their job, not yours.

---

## What this skill does NOT do

- **Do not touch Anthropic memory.** Do not read from `~/.claude/projects/{hash}/memory/`. Do not reference it in any file. Do not write to it. Memory is its own system with its own write logic; leave it alone.
- **Do not run a detection algorithm.** No priority orders, no multi-source resolution, no scanning for patterns. Look around with Read/Glob if you need to, but the design here is "trust the agent's context."
- **Do not be exhaustive.** Update what changed. Skip what didn't. If the session was tiny and nothing happened, the required output is still the CLAUDE.md pointer check AND a one-line confirmation that the index exists and is current.
- **Do not write state update to claude.md**. Claude.md is not a durable handoff for the purposes of this skill and should only be used to point to the active or just created state file. 

---

## End-of-run summary

After your changes, give the user a tight summary:

- What was updated or created (1 line per file)
- Always state what happened to the index (created / updated / confirmed current); if it is not in your summary, you skipped a required step, so go back
- If anything notable was logged to the learning log, mention the entry briefly

Aim for under 100 tokens total, if possible. The user is about to /clear or /compact — they don't need a long report.

Example:
```
Updated startup.md (Current Focus + What's Next), prepended one [agent] entry to learning-log.md, refreshed _index.md, ensured CLAUDE.md pointer.
```
