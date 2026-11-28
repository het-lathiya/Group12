-- Refuse downgrade while GROQ rows exist; never rewrite or delete generation history.
alter table public.ai_generations drop constraint ai_generations_provider_check;
alter table public.ai_generations add constraint ai_generations_provider_check
  check (provider in ('GEMINI','MOCK','FINETUNED_MODEL'));
