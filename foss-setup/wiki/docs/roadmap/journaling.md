# Roadmap — journaling

7 task(s). Status mirrors `docs/progress.json` (the source of truth).

| Task | Title | Status | Effort |
|---|---|---|---|
| `journal-01` | Scaffold the journaling stack (Memos + n8n + faster-whisper) on the mini and bring it up | ✅ done | 2 hr |
| `journal-02` | Create the Memos account + API token, wire the memo.created webhook to n8n, confirm events arrive | ✅ done | 1 hr |
| `journal-03` | Build + test the journal-analyze n8n workflow (LLM coaching + loop-safe comment write-back) | ✅ done | 3 hr |
| `journal-04` | Wire the optional faster-whisper server-side transcription branch | ⬜ open | 2 hr |
| `journal-05` | Add the Open WebUI Journaling Coach preset + Save-to-Journal function | ⬜ open | 2 hr |
| `journal-06` | Journaling stack closeout: README, backup/export, end-to-end monitoring, wiki, coverage | ⬜ open | 2 hr |
| `journal-07` | Phase 2 (deferred): IGDB game-metadata enrichment for #gamelog entries | ⏸️ deferred | 3 hr |

[← Roadmap overview](index.md)
