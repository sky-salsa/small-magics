---
name: hand-up
version: 1.1
description: Pick up a project with prior saved state. Ensures referenced state documents get read in full. Trigger on /hand-up, "handup", "hand up", "pick up where we left off", or "where did we leave off?"
---

# /hand-up — Pick Up From a Hand-Down

You've been dropped into a project with handoff state from a prior session. **Before doing anything else, read the handoff documents in full.**

> **Note on former names.** This skill was previously named `/handon`, and its partner `/hand-down` was previously `/handoff`. Mentions of `/handoff` or `/handon` in a repo's own documents are almost always references to those former names — you are allowed and encouraged to update them to `/hand-down` and `/hand-up` whenever you encounter them. Do not confuse this with the separate `/handoff` skill that may appear in your skills list: that is an unrelated skill by a different author, not an earlier version of this one.

## What to do

1. **Open `CLAUDE.md`** in the project root. It usually contains a pointer line saying to read a specific state file first. If there's no such pointer, look for `startup.md`, `state.md`, `handoff.md`, or another similarly-named state file.

   If `CLAUDE.md` lists multiple scoped workstreams, identify which one is yours from your context. If that's clear, read that subdir's docs in full. If it's not clear, ask the user which workstream before reading anything.

2. **Read the state file in full.** The Read tool defaults to 2000 lines and silently truncates past that. If the file is longer, re-invoke Read with an explicit `limit` parameter large enough to capture the entire file. Do not assume you have the picture after a default read.

3. The state file will reference further files that must be read. **Read each of those in full as well, if the core state file instructs you to do so.** Same rule applies. No partial reads on load-bearing context.

4. **Read the index in full.** This is your map of the project guiding you to where files are when you need them. Do not read files until they are needed. 

5. Once you have actually read all explicitly necessary referenced documents fully, give a tight one-paragraph rundown of where things stand and what you understand the next step to be. Then wait for the user to confirm or redirect before acting.

## Keep the index current as you work

The five steps above run once, at pickup. This one runs for the rest of the session.

The project keeps an index file (`_index.md`), a one-line-per-doc catalog of what exists so whoever picks this up next can see the whole library without opening it. It only stays useful if it stays current. So as you work, update it the moment you create, rename, move, or delete a doc or asset it tracks: edit the one-line entry as part of writing the file, not in a cleanup pass saved for later. If a change of yours leaves an entry wrong, fix it then.

The index file is vitally important and is the best means of avoiding burning unnecessary context or tokens. While /north-star discipline is important it must be balanced. Don't guess at things directly relevant to the current task or conversation, but do not read more context than is necessary to verify. 

Keep entries to the same kind of thing already in there: project docs and assets, not source code, one line each. Maintaining it as you go is the whole reason it can be trusted; the alternative, rebuilding the whole index in one sweep at the end of the session, is exactly the batch chore that gets rushed or skipped.

## Why this exists

The `/hand-down` skill curates which files the next agent should read, but without explicit instruction agents default to partial reads, especially on long files. The result is a confident-sounding pickup with quietly missing context. This skill closes that loop.

---

North Star Discipline: And as always, remember our core north star. The crucible of logic that will tend to steer us right: we don't accept any belief or theory as true until it is abundantly verified. until then, any plausible explanation of understanding of things should be understood to be just a theory or an assumption until otherwise proven to have substantive and verifiable merit.
