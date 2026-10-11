# MerryMapped

A Christmas-markets trip planner (Germany, Belgium, France, by train) built on a legal engine.

Two promises, both enforced in code:
1. You never land at a closed market.
2. The app never uses data it isn't allowed to use.

## Layout

| Folder | What's in it |
|---|---|
| `backend/` | Python (FastAPI): legal engine, onboarding agent, planner, checker |
| `frontend/` | Next.js (TypeScript, Tailwind, shadcn/ui, MapLibre): the web app |
