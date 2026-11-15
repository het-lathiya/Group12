Offline evaluation: datasets, run results and reports.

## Prompt version (IMD-195)

The generation suite sends the frozen requests of the dataset; `trips/v1` requests name `itinerary_generate` v1. To evaluate another version, pass it explicitly:

    make eval PROVIDER=MOCK DATASET=trips/v1 ARGS='--prompt-version v3'

The allowed values are the `itinerary_generate` versions in the prompt registry. The option overrides the version in every request (a gr-2 version gets the request grounded with no passages) and the run record states `prompt_version`, `prompt_sha256` (the template files' hashes), the schema versions and `prompt_version_overridden`. `PROMPT_TEMPLATE_VERSION` does not change what this suite sends.

A report quotes `prompt_version` from `run.json`, never from the command or the environment. MOCK does not read the prompt text, so a MOCK run shows only that the harness accepts the version; v3 is activated only after a MOCK run and one GEMINI run of v3 on `trips/v1` (IMD-195).
