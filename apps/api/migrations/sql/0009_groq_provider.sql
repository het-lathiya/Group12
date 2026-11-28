-- IMD-223: the optional second provider updates the existing generation row.
alter table public.ai_generations drop constraint ai_generations_provider_check;
alter table public.ai_generations add constraint ai_generations_provider_check
  check (provider in ('GEMINI','GROQ','MOCK','FINETUNED_MODEL'));
