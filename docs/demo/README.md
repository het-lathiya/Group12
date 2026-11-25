# Demo folder

**DRAFT — completed after SG-7 (IMP-801)**

| File | Purpose | State |
| --- | --- | --- |
| [demo-script.md](demo-script.md) | The six-minute script, with a path for the switch ON and one for OFF | draft (Nidhi) |
| [rehearsal-log.md](rehearsal-log.md) | Rehearsal dates, times and defects | empty template |
| [pre-demo-checklist.md](pre-demo-checklist.md) | The steps of demo day, each with a name and time (IMP-803) | empty template (Malhar, Jeel) |

## How to run the demo

1. Complete the pre-demo checklist.
2. Open the production web address: pending (Kirtan, IMP-801).
3. Follow the script: path A if any-city mode is ON in production, else path B.

## Fallback on the presenter machine (IMP-803)

The app with the MOCK provider, needing no key and no network call to Gemini. Set it up before the demo with [local-setup.md](../guides/local-setup.md):

```sh
make stack-up
make db-migrate
make seed          # Sampleton, labelled SAMPLE; add SEED_DIRS=data/places/ahmedabad for Ahmedabad
make api           # terminal 1, with AI_PROVIDER=MOCK
make web           # terminal 2
```

`AI_PROVIDER=MOCK` is the default of the local env file. Keep any-city mode OFF there, or use `LIVE_DATA_PROVIDER=FAKE` with its SAMPLE cities. To show the failure path, start the API with `MOCK_PROVIDER_SCENARIO=timeout`. Say that MOCK answers are fixed SAMPLE notes, not Gemini.

## Backup video

| Item | Value |
| --- | --- |
| Location | pending (Nidhi) |
| Duration | pending (Nidhi) |
| Recorded on, with which release | pending (Nidhi) |

The video is not stored in Git (no large binary).
