# Commit ID map after the committer rewrite (IMD-208)

Date: 18 November 2026. Decision: IMD-208.

On this date the history of main was rewritten once so that every commit's committer name and email equal its author's. Commit IDs quoted in records before 18 November 2026 are old IDs; files, authors and dates are unchanged. The one commit made as kirtan-S111 is now authored by Kirtan's team identity.

The table lists the 423 commits of main at the time of the rewrite, newest first.

| Old | New | Author | Subject |
| --- | --- | --- | --- |
| 00d09e9 | bd4cf4a | Krrish Kamani | docs(e2e): IMP-701 run evidence for the regression suite |
| c74515a | 38debf9 | Manasvi Rathore | fix(shell): IMP-104 trip navigation fits 360 and 768 px without hiding tabs (IMD-207) |
| c645138 | fcbbeb5 | Nidhi Chauhan | docs(decisions): RUN-081d IMD-207 app shell layout fix |
| 708150b | 155724d | Krrish Kamani | test(e2e): IMP-701 read the generation mode from the 202 body |
| d93e9af | c5fc7cd | Krrish Kamani | test(e2e): IMP-701 fix the retime, warnings-panel and provider-failure specs; repeat_each input and run evidence |
| df15467 | a122fb7 | Krrish Kamani | fix(itinerary): IMP-506 lock toggle name contains its visible label (TC-383) |
| f89c749 | 9ef26c8 | Manasvi Rathore | fix(costs): IMP-507 keyboard-reachable scroll regions in the cost breakdown |
| 1837547 | 6b1a9b6 | Nidhi Chauhan | docs(decisions): RUN-081c IMD-206 provider-failure setup and accessibility defects |
| 4b67c60 | 4566bbd | Jeel Fefar | fix(web): IMP-610 narrow versions data before rendering the list |
| 600eb9b | ce62e17 | Jeel Fefar | fix(web): IMP-610 versions page shows not-found for another user's trip |
| fd68bf7 | 9db3c10 | Mohammad Junaid Kureshi | test(authz): IMP-702 wrong-issuer case and corrected TC-347 evidence |
| 91bfa64 | df1918c | Het Lathiya | fix(auth): IMP-702 refuse tokens from a foreign issuer (TC-347, IMD-204) |
| 858429f | 9c0fd27 | Malhar Mer | chore(env): IMP-105 raise the local sign-in rate limit for the E2E suite (IMD-203) |
| 5d32ff4 | f063a81 | Nidhi Chauhan | docs(decisions): RUN-081b IMD-203 to IMD-205 |
| 8414342 | 6f9e454 | Krrish Kamani | test(e2e): IMP-701 regression suite for E2E-01..08, floor, 360 px, keyboard and provider-failure projects |
| e60fbe3 | 2b13aab | chaudhari kirtan sandipbhai | chore(web): IMP-214 clear the client.ts lint warning |
| 3321cc3 | f6efa07 | chaudhari kirtan sandipbhai | test(security): IMP-702 CORS/header checks and secret-scan review |
| c382292 | 80ccd1a | Het Lathiya | docs(progress): IMP-702 auth-fixes record, no fix needed |
| b2ce938 | aed563a | Mohammad Junaid Kureshi | test(authz): IMP-702 route inventory, ownership re-run, injection corpus and security report |
| f39dca5 | 5f627c3 | Nidhi Chauhan | docs(decisions): RUN-081 IMD-202 Sprint 7 batch order |
| a4c2a0b | c6661e1 | chaudhari kirtan sandipbhai | docs(progress): IMP-699 SG-6 gate with listed gaps, sprint-6 index, deferred list |
| 002ba49 | 36aca4f | chaudhari kirtan sandipbhai | ci(e2e): IMP-699 features_disabled input for the floor journey (TC-372) |
| e311ead | f859574 | Nidhi Chauhan | docs(decisions): RUN-080 IMD-200 and IMD-201 |
| fd7ae14 | 16bb95c | Manya Rana | docs(eval): RUN-079 prompt v3 evaluation on MOCK and Gemini from main |
| ba18266 | 2e0e058 | Nidhi Chauhan | docs(progress): RUN-079 decision-record part record |
| 1df32c1 | 627c0dc | Nidhi Chauhan | docs(decisions): RUN-079 IMD-199 evaluation default prompt version |
| 3a68439 | 484db00 | Manya Rana | fix(generation): RUN-078 reserve lunch in rule-based full days (IMD-196) |
| 45d52c3 | 001d1df | Manya Rana | feat(eval): RUN-078 prompt version option and version in reports (IMD-195) |
| f144d71 | 22be0c5 | Nidhi Chauhan | docs(decisions): RUN-078 IMD-195 to IMD-198 and §8.4 MOCK wording |
| b715d26 | 9ab2d12 | Krrish Kamani | fix(web): RUN-077 journey waits for the settled dashboard before Open latest |
| 7d55c8d | eea8592 | Malhar Mer | test(itinerary): RUN-077 keep one backup when versions are off (IMD-191) |
| 0c6ff74 | efaf35a | Nidhi Chauhan | fix(ai): RUN-077 MOCK ok scenario plans meal slots (IMD-189) |
| 743b979 | cc19566 | Manya Rana | fix(generation): RUN-077 lunch slot on relaxed full days (IMD-189) |
| 0b71d37 | 2378056 | Manya Rana | docs(eval): RUN-077 prompt v3 MOCK evaluation from main BASE |
| 883da86 | d12fbdb | Nidhi Chauhan | docs(decisions): RUN-077 IMD-193 and IMD-194 |
| 0e15ae7 | 17dcaa8 | Krrish Kamani | fix(web): IMP-607 scan regenerate toasts after their enter animation |
| f7ba78c | 6ed4450 | Krrish Kamani | fix(web): IMP-607 verify regeneration feedback and loading controls |
| 84359ce | dd5246b | Nidhi Chauhan | fix(generation): IMP-607 validate scoped assertions and destination currency |
| 9cccbf1 | 6b4e115 | Het Lathiya | fix(itinerary): IMP-607 verify save types and regeneration transaction fixtures |
| 0e2db53 | 91c9082 | Krrish Kamani | feat(web): IMP-607 regenerate day and regenerate all controls |
| 781e8cd | fd70d6e | Het Lathiya | feat(itinerary): IMP-607 merge regenerated day and full regeneration around locks |
| d075cc4 | d06a811 | Nidhi Chauhan | feat(generation): IMP-607 day-scoped request and pipeline scope |
| 0524d2b | 5f5c78e | Het Lathiya | feat(generation): IMP-607 regenerate day and whole itinerary endpoints |
| 89f54db | 9ad8a5d | Nidhi Chauhan | docs(decisions): RUN-076 IMD-188 to IMD-192 and §6.6.3 amendment |
| ce2c63d | 2f64bf9 | Krrish Kamani | docs(acceptance): IMP-611 findings template |
| 6f46ca0 | 46d6ad4 | Mohammad Junaid Kureshi | docs(acceptance): IMP-611 usability session 1 plan template |
| 3769bab | 5a25fee | Krrish Kamani | feat(web): IMP-609 IMP-608 summary tab and budget alert on the costs page |
| b991141 | b0e7dbd | Jeel Fefar | feat(web): IMP-610 versions tab in the trip navigation |
| 428b68c | 89de20d | Manasvi Rathore | feat(web): IMP-604 explore tab in the trip navigation |
| 07c4f7e | 0ea0098 | Manasvi Rathore | fix(web): RUN-075 destructive button hover contrast |
| 3ba7193 | 45786d1 | Krrish Kamani | feat(web): IMP-608 BudgetAlert component |
| 89c52f5 | 5a9e073 | Krrish Kamani | feat(web): IMP-609 summary page and print layout |
| a8065f9 | db01336 | Jeel Fefar | feat(web): IMP-604 PlaceDetailDrawer with labelled facts |
| 7b1437a | 0406bcd | Manasvi Rathore | feat(web): IMP-604 PlaceFilterBar with URL filter state |
| 97fe1f9 | a74fa7f | chaudhari kirtan sandipbhai | chore(contracts): IMP-602 IMP-604 IMP-605 IMP-608 IMP-609 IMP-610 IMP-601 regenerate OpenAPI and web types |
| 53c8664 | a435af0 | Manal Patel | feat(trips): IMP-602 archived trips are read-only on edit routes |
| de2fc60 | fbbfade | Het Lathiya | feat(auth): IMP-601 profile API and page with wizard prefill |
| 22e9601 | e9a025f | Manasvi Rathore | feat(web): IMP-602 dashboard and TripCard |
| b6c2b3a | 3c9a813 | Manal Patel | feat(budget): IMP-608 budget alerts and contingency buffer |
| bc0146b | 8ed3f9c | Manal Patel | feat(trips): IMP-602 rename, duplicate, archive, delete and purge job |
| 24953cd | e86f12f | Manya Rana | feat(ai): RUN-075 itinerary_generate prompt v3 (IMD-180, IMD-181) |
| a74e8d1 | d1f00aa | Manya Rana | feat(generation): IMP-606 meal slots in request builder and fallback planner |
| 60e899d | 4cd4221 | Malhar Mer | feat(generation): IMP-606 food places, meal-slot retrieval and item display |
| f49b977 | 6932e7a | Het Lathiya | feat(itinerary): IMP-609 trip summary API |
| 2bdfd9d | 3d929ad | Malhar Mer | feat(itinerary): IMP-610 restore transaction and version retention |
| 67565fe | a7e59a0 | Jeel Fefar | feat(itinerary): IMP-610 snap-1 versions, list, save and versions page |
| 582eae0 | 070039f | Jeel Fefar | feat(places): IMP-605 saved places with wishlist switch |
| f53c674 | bb273b6 | Malhar Mer | feat(places): IMP-604 search filters, place detail and indexes |
| 13e0bc6 | a22c37f | Nidhi Chauhan | docs(decisions): RUN-075 IMD-187 and IMD-183 amendment note |
| a6307c3 | 9d1bdf5 | chaudhari kirtan sandipbhai | docs(progress): IMP-599 SG-5 gate record with listed gaps |
| 0945cab | fb87564 | chaudhari kirtan sandipbhai | ci(e2e): IMD-185 run E2E on every push to main again |
| 599cad0 | 7f5b66f | Nidhi Chauhan | docs(decisions): record IMD-185 and IMD-186 |
| 43a4240 | 0374bf1 | chaudhari kirtan sandipbhai | ci: IMD-184 a pull-request edit re-runs only the attribution job |
| 74e001c | 9d80540 | Het Lathiya | fix(api): PD-RUN-071c-1 commit the transaction before the response |
| c5ab3b5 | 41d57fa | Nidhi Chauhan | docs(decisions): record IMD-177 to IMD-184 |
| a72d07a | 071f076 | chaudhari kirtan sandipbhai | ci(e2e): IMD-183 run E2E by dispatch only |
| ab94cd5 | 64f3333 | Krrish Kamani | fix(a11y): IMP-513 restore focus after the moved item renders |
| 06af2f7 | 4e8b210 | Manasvi Rathore | fix(ui): IMP-104 button animates colours only |
| 05706e8 | 748b36e | Manasvi Rathore | fix(map): IMP-508 load the map worker in the production build |
| 864c78f | ad00d45 | Krrish Kamani | fix(a11y): IMP-513 dashboard colour contrast |
| 4e0c232 | e274737 | Krrish Kamani | test(e2e): PD-RUN-070b-2 record axe violation targets on every attempt |
| a9c3adc | c0b76a7 | chaudhari kirtan sandipbhai | ci(e2e): PD-RUN-070b-1 run the map spec in the E2E workflow |
| aec7caa | 3cacb13 | Manasvi Rathore | fix(map): PD-RUN-070-1 OpenStreetMap credit in the map panel |
| 736da4d | e35d07d | Krrish Kamani | fix(a11y): IMP-513 warning severity headings and journey findings |
| b293041 | 82cd5a3 | Nidhi Chauhan | docs(evaluation): IMP-514 first Gemini baseline |
| 61c5003 | fea7b8c | Manasvi Rathore | test(map): IMD-173 tile-abort fallback and attribution E2E |
| 85aa855 | 24d93ec | Krrish Kamani | feat(a11y): IMP-513 keyboard and assistive-technology support |
| e7bbfec | 4df4b3d | Nidhi Chauhan | fix(ai): PD-RUN-069-1 MOCK default proposal fits curated hours |
| 15475eb | 1bdd05c | Het Lathiya | fix(itinerary): IMP-506 integration fix |
| 5ae2e52 | 44e21a8 | Mohammad Junaid Kureshi | fix(validation): IMP-501 integration fix |
| ad1fb9e | 743a1c3 | Manal Patel | fix(validation): IMP-501 integration fix |
| 0dadfb2 | 7a6ed74 | Nidhi Chauhan | fix(decisions): IMP-507 integration fix |
| fc7da1a | 756f601 | Krrish Kamani | feat(trips): IMP-510 trip edit page and stale-plan banner |
| 5f0f5b7 | f9c5e17 | Manasvi Rathore | feat(trips): IMP-503 pace control posts pace |
| 5cec0de | eb35ede | Manasvi Rathore | feat(costs): IMP-507 cost breakdown tables and label review |
| 66f684c | 3390eda | Krrish Kamani | feat(itinerary): IMP-506 lock toggle on item cards |
| 91b0636 | ba79e35 | Krrish Kamani | feat(itinerary): IMP-505 alternatives dialog |
| aa7cccb | b96759e | Malhar Mer | feat(itinerary): IMP-504 place picker with undo and stale-plan reload |
| 5f53777 | 3ce5ab1 | chaudhari kirtan sandipbhai | fix(schemas): IMD-159 plain-language currency error |
| 70b1ba1 | 6a5b2f9 | chaudhari kirtan sandipbhai | feat(core): IMP-511 rate limits and daily generation caps |
| bd6e5eb | f79c388 | Manal Patel | feat(validation): IMP-501 budget conflict findings |
| e3ebdbd | ee686ce | Mohammad Junaid Kureshi | feat(validation): IMP-501 opening-hours and overpacked-day checks |
| 7ea14e7 | 5c212be | Het Lathiya | feat(itinerary): IMP-506 lock and unlock items |
| 28d265c | ec3893f | Manya Rana | fix(evaluation): IMP-514 run record names a commit on main |
| 2bf1bfe | adde4ed | Nidhi Chauhan | docs(decisions): record IMD-168 to IMD-176 |
| 4c6c693 | 7c239b3 | Het Lathiya | fix(itinerary): IMP-505 integration fix |
| 143e549 | 6e2baac | Het Lathiya | fix(itinerary): IMP-504 integration fix |
| 52788fd | 61a84f7 | Nidhi Chauhan | fix(validation): IMP-502 integration fix |
| f292ed3 | 829885f | chaudhari kirtan sandipbhai | chore(contracts): regenerate OpenAPI for IMP-504, IMP-505, IMP-507, IMP-509, IMP-510 |
| ba78e4d | 1eebb0c | Manasvi Rathore | feat(map): IMP-508 map with numbered markers and list fallback |
| e2a642e | 5551466 | Mohammad Junaid Kureshi | test(ai): IMP-512 provider contract suite |
| 8133a07 | c02fb5f | Jeel Fefar | feat(places): IMP-509 browse places with source labels |
| 13248d0 | 41f29a6 | Manal Patel | feat(trips): IMP-510 trip settings edit and stale-plan flag |
| 0c517f7 | 26c531a | Manal Patel | feat(budget): IMP-507 daily and category cost breakdown |
| c7bef51 | 0113035 | Manya Rana | feat(evaluation): IMP-514 evaluation run records |
| 662c9da | b5b8d2f | Manya Rana | feat(generation): IMP-503 pace presets and day grouping |
| 03f54c9 | caf424c | Het Lathiya | feat(itinerary): IMP-505 ranked alternatives and replace edit |
| def5241 | 7f9d8fa | Het Lathiya | feat(itinerary): IMP-504 add-place edit and stale-edit rejection |
| c29cd47 | 1cfbaff | Nidhi Chauhan | docs(decisions): record IMD-167 |
| 0b90bc2 | 3f6e97c | Nidhi Chauhan | feat(validation): IMP-502 bounded repair with one model retry |
| 26bac9d | 48e8e4b | chaudhari kirtan sandipbhai | docs(progress): IMP-499 SG-4 gate record, Sprint 4 index and cut-list checkpoint |
| 813141d | 576b659 | Nidhi Chauhan | docs(spec): record IMD-159 to IMD-166 and confirm IMD-148 |
| ec6973a | df6287d | Krrish Kamani | fix(web): IMP-410 dashboard New trip action and no-drafts hint |
| c90f3e4 | 638dfd3 | Krrish Kamani | test(e2e): IMP-414 removal toast check back to a hard assertion |
| 5315c6c | 7d47b24 | Manasvi Rathore | fix(web): IMP-408 removal toast and focus survive the card unmount |
| b6bec3c | 3dc5d6b | Krrish Kamani | test(e2e): IMP-414 full journey with edits and a manual staging job |
| d78180f | 8ac90a8 | Mohammad Junaid Kureshi | test(e2e): IMP-414 journey fixtures, trip reset and the Sprint 4 report |
| ee905c7 | 7131c92 | Mohammad Junaid Kureshi | test(evaluation): IMP-318 two identical MOCK retrieval runs |
| dfeba67 | 4a1f2bb | Mohammad Junaid Kureshi | feat(evaluation): IMP-318 retrieval metrics and the retrieval suite |
| 7313be1 | 5d0eeb8 | Mohammad Junaid Kureshi | feat(evaluation): IMP-318 labelled retrieval dataset v1 with review manifest |
| 3359b67 | e42b3f8 | Jeel Fefar | feat(data): IMP-402 two saved SAMPLE itineraries built by the rule-based planner |
| 4554294 | bf1f89c | Jeel Fefar | feat(generation): IMP-402 sample itinerary loader resolving external refs |
| 4e6bcbd | 7b3a5d3 | Krrish Kamani | fix(web): IMD-154 fallback notice wording and stable wizard tests |
| ebd18e9 | f1dd042 | Malhar Mer | fix(places): IMD-127 API-16 answers 404 for an inactive destination |
| 39655db | 6652e64 | Het Lathiya | fix(auth): IMD-140 clock leeway and an ES256 token test |
| fb983f4 | 772e928 | chaudhari kirtan sandipbhai | chore(devops): SG-3 follow-ups, IMD-138 trust policy and staging window guide |
| 276b2f8 | b13e632 | Nidhi Chauhan | docs(spec): record IMD-137 to IMD-155 and align the spec text |
| 8c3997b | 8d8d48a | Manasvi Rathore | feat(web): IMP-409 drag and keyboard move controls |
| 71f888b | 65aa4d8 | Manasvi Rathore | feat(web): IMP-408 item editor for retime and remove |
| dae80b5 | 3c1a97e | Het Lathiya | feat(itinerary): IMP-409 move route with renumbering across days |
| 6271cf5 | 3d63f33 | Het Lathiya | feat(itinerary): IMP-408 remove and retime routes on the edit pipeline |
| d7625c7 | 9f72457 | Krrish Kamani | feat(web): IMP-403 fallback notice and paused-AI option |
| 2f056fa | 27e33a7 | Manasvi Rathore | feat(web): IMP-405 warnings panel grouped by severity |
| 9d52561 | 02eec3a | Nidhi Chauhan | feat(generation): IMP-403 failure outcomes with labelled fallback |
| 5e0188e | 068174e | Het Lathiya | feat(itinerary): IMP-407 atomic edit pipeline with plan revision |
| 3f501f2 | 2c215c5 | Jeel Fefar | feat(validation): IMP-405 persist findings with suggested fixes and API-32 |
| 84d1973 | 2bda3fa | Krrish Kamani | feat(web): IMP-406 AI-written labels on itinerary cards |
| 3e3c412 | 5d373af | Manya Rana | feat(generation): IMP-406 keep must-visit places and explicit constraints |
| a20f8ba | 17551d6 | Manya Rana | fix(validation): IMD-126 drop items outside the trip instead of failing |
| e2715b0 | 5de3eaa | Nidhi Chauhan | feat(ai): IMP-401 bounded retries and circuit breaker in the Gemini adapter |
| 6339698 | cf2ce5c | Malhar Mer | feat(generation): IMP-402 deterministic rule-based fallback planner |
| fb31367 | 713caa9 | Krrish Kamani | test(e2e): axe checks in Playwright specs |
| e3a4184 | 63475c1 | Manasvi Rathore | fix(web): IMD-135 show the year in source retrieval dates |
| 1f60fe8 | a603748 | Manasvi Rathore | feat(web): IMP-412 loading, empty and error states with error catalogue |
| bdd4cb1 | edd173c | Krrish Kamani | feat(web): IMP-411 budget settings form and source badge variants |
| e193ce0 | b9f9b40 | Krrish Kamani | feat(web): IMP-410 continue draft and open latest |
| 64c503a | da2e1e5 | Manal Patel | feat(budget): IMP-411 transport allowance, stay budget and price labels |
| 36de969 | 29240f5 | Manal Patel | feat(trips): IMP-410 draft trips and latest itinerary API |
| 1bf3bc5 | b86f53e | Mohammad Junaid Kureshi | fix(deploy): IMP-218 pass task definitions to the AWS CLI as files |
| 59f174e | f8e4315 | Mohammad Junaid Kureshi | fix(deploy): IMP-218 read the Express Mode task definition from the primary deployment |
| 16839a0 | dfad441 | Manya Rana | feat(evaluation): IMP-413 offline evaluation harness with versioned metrics |
| 2c8acc8 | 1e8bd2f | Mohammad Junaid Kureshi | feat(validation): IMP-404 must-visit, unknown-place and trip-date rules |
| 68f02d1 | c5146d1 | Manal Patel | feat(validation): IMP-404 rule-registry validator with overlap and transfer rules |
| f7f3c51 | 30ccb58 | Nidhi Chauhan | docs(spec): IMP-399 record IMD-124 to IMD-136 and align the spec |
| fe02488 | 6c7f87f | Nidhi Chauhan | docs(progress): IMP-399 SG-3 gate record and Sprint 3 index |
| 15a6656 | 6db4c88 | Mohammad Junaid Kureshi | test(authz): IMP-215 stabilise test tokens in the ownership suite |
| 5eaf19f | db5ce57 | Nidhi Chauhan | docs(ai): IMP-113 Gemini account facts and TC-029 live result |
| d5b5c1b | 9b4df4b | chaudhari kirtan sandipbhai | chore(infra): SG-3 staging template switches to Gemini and seeds Ahmedabad |
| 4b10e3f | 6b18e48 | Nidhi Chauhan | fix(ai): IMP-301 state removed limits in the Gemini wire-schema descriptions |
| 589f613 | f725a43 | Nidhi Chauhan | fix(ai): IMP-301 send Gemini a wire schema without serving-limit keywords |
| 73008e4 | 6098f07 | Manasvi Rathore | test(web): IMP-317 sources component and accessibility checks |
| 2cb2620 | 03250a3 | Manasvi Rathore | feat(web): IMP-317 sources disclosure on AI-written item notes |
| 8948212 | 025e8de | Het Lathiya | feat(itinerary): IMP-316 saved citations and sources in the itinerary read |
| cc225c9 | 57a53ed | Manya Rana | feat(ai): IMP-316 grounded request gr-2, template v2 and validated citations |
| 85137d3 | 8181fea | Malhar Mer | docs(data): IMP-314 Ahmedabad guide quality report and gate run |
| 0fd0252 | 71fda68 | Krrish Kamani | feat(data): IMP-314 Ahmedabad destination guides |
| d8d79d6 | 8582e1e | Manasvi Rathore | feat(web): IMP-309 day-wise itinerary view with source and AI labels |
| 217d0d1 | 369b22b | Het Lathiya | feat(itinerary): IMP-309 itinerary read fields for the day-wise view |
| 1681b41 | d016bfc | Manal Patel | feat(budget): IMP-308 budget engine, item costs and costs API |
| b1d82ae | a632e16 | Het Lathiya | feat(generation): IMP-308 deterministic schedule recalculation from routing |
| 0375abf | 137de5d | Jeel Fefar | feat(rag): IMP-315 hybrid retrieval with semantic scores, guide passages and lexical fallback |
| e5f5e7a | 051a35f | Manal Patel | feat(rag): IMP-313 corpus ingestion, chunking and make rag-index |
| 394ba7e | d949218 | Mohammad Junaid Kureshi | test(validation): IMP-306 prompt-injection output cases |
| f61f639 | 2a88c53 | Manya Rana | feat(validation): IMP-306 io-1 limits and place-ID output check |
| 654b4f7 | b844ecf | Krrish Kamani | feat(web): IMP-305 privacy notice and live progress on the generate page |
| 9144cc6 | f8c7489 | chaudhari kirtan sandipbhai | feat(api): IMP-302 provider metadata and status in readiness |
| d001553 | 697339a | Nidhi Chauhan | feat(generation): IMP-305 full generation pipeline through the active provider |
| 3f0658b | 93d9e77 | Het Lathiya | feat(generation): IMP-305 job progress states, privacy-notice flag and timeout-after-commit fix |
| 8a504c0 | edf3fea | Nidhi Chauhan | feat(ai): IMP-312 embed_texts on ModelProvider with Gemini and deterministic MOCK embeddings |
| 7974da0 | 4812515 | Manya Rana | test(ai): IMP-301 Gemini setup facts and recorded-response adapter tests |
| 520f362 | 0e2b20b | Nidhi Chauhan | feat(ai): IMP-301 Gemini adapter with structured output and error mapping |
| f282b97 | d867294 | Manya Rana | feat(ai): IMP-303 normalized generation request with redacted notes and prompt size control |
| 4387f47 | b11c9f8 | Mohammad Junaid Kureshi | feat(eval): IMP-310 evaluation dataset v1 with 15 SAMPLE cases |
| 26092b4 | 7fdc1c5 | Mohammad Junaid Kureshi | feat(routing): IMP-307 OpenRouteService client with route cache and fallback |
| f71b0fb | 531f2b6 | Jeel Fefar | feat(generation): IMP-304 preference-weighted scoring and shortlist ranking |
| d485f13 | beea951 | Malhar Mer | feat(generation): IMP-304 candidate retrieval and hard-constraint filters |
| 4f20bfc | 0d15847 | chaudhari kirtan sandipbhai | docs(progress): IMP-299 SG-2 record fixes, decision status and personal data removal |
| d4b7202 | 3cf8eb5 | chaudhari kirtan sandipbhai | docs(spec): IMP-299 record IMD-121 to IMD-123 and align A1 with JWKS sign-in |
| fc69e7a | a8b6e6d | chaudhari kirtan sandipbhai | docs(progress): IMP-299 SG-2 gate record and Sprint 2 index |
| 0b361fc | cccb20a | chaudhari kirtan sandipbhai | docs(progress): IMP-216 add whole-task part record |
| 4ae3111 | 8831f49 | chaudhari kirtan sandipbhai | test(e2e): IMP-216 walking-skeleton journey and e2e workflow |
| dd2961b | 3e280ed | Mohammad Junaid Kureshi | fix(infra): IMP-218 JWKS sign-in and deploy-role permissions for the AWS set-up |
| 04f13c1 | b161b09 | Mohammad Junaid Kureshi | ci(deploy): IMP-218 AWS deploy workflows and release task |
| b1dcdb6 | a6840a6 | Manasvi Rathore | feat(web): IMP-218 production web image with build-time public settings |
| 2c66e14 | 5edac77 | Het Lathiya | docs(progress): IMP-210 record the job-timeout race fix |
| d921e16 | e28760d | Het Lathiya | test(generation): IMP-210 expire the job timeout during the provider call |
| f8eee92 | 256278c | chaudhari kirtan sandipbhai | docs(progress): IMP-217 add whole-task part record |
| 01b4882 | fa66dcc | chaudhari kirtan sandipbhai | docs(infra): IMP-217 AWS set-up guide, secrets register and deployment guide |
| 23f9b4a | 467da23 | chaudhari kirtan sandipbhai | feat(infra): IMP-217 AWS staging set-up scripts and service templates |
| f41fd88 | e2e48fd | Jeel Fefar | docs(data): IMP-206 Ahmedabad quality report and lead-curation record |
| f08e6c2 | 4553e07 | Malhar Mer | feat(data): IMP-206 Ahmedabad opening hours and prices with sources |
| f19ff0b | 5d66489 | Jeel Fefar | feat(data): IMP-206 Ahmedabad destination, sources and verified place list |
| 94849c6 | d01e1db | Malhar Mer | docs(progress): IMP-115 record the plan under IMD-120 |
| 7d5aeca | c69e1ba | Malhar Mer | docs(decisions): IMP-115 record the destination decision |
| 42bfd27 | 4757dc6 | Malhar Mer | docs(data): IMP-115 record the destination plan, sources and minimum |
| 8892c45 | 617218a | Malhar Mer | docs(progress): IMP-115 add whole-task part record with the outcome needed |
| 2633214 | 86607f9 | Malhar Mer | docs(data): IMP-115 seed-data plan and destination decision templates |
| 51181ba | 758bc5d | Malhar Mer | docs(data): IMP-115 curated destination file format and curator checklist |
| 696a766 | 6d9da1b | Krrish Kamani | docs(progress): IMP-213 record the flaky timeout test fix |
| d314cb0 | dbb8d10 | Krrish Kamani | test(web): IMP-213 make the 160 s timeout test deterministic |
| ea154bd | 9b794aa | Jeel Fefar | docs(spec): IMD-120 desk-checked seed data and plan for destination 1 |
| 0a0b8a2 | fbb23ef | Krrish Kamani | docs(progress): IMP-213 add whole-task part record with screenshots |
| 1072912 | 7c7fbed | Krrish Kamani | test(web): IMP-213 polling state machine and itinerary rendering tests |
| b21e74a | 1c23666 | Krrish Kamani | style(web): IMP-213 set the control radius to 8 px as the design guide states |
| 4f81e45 | 7610e8c | Krrish Kamani | feat(web): IMP-213 read-only itinerary with day index, tabs and timeline |
| d975461 | 712c80e | Krrish Kamani | fix(web): IMP-213 stream the signed-in guard behind Suspense so dynamic trip routes build |
| a4e1a7a | 1a53c2b | Krrish Kamani | feat(web): IMP-213 generate page with one-request start and resumable polling |
| 6c3bb65 | 84ba955 | Krrish Kamani | feat(web): IMP-213 generation progress with back-off, timeout and failure states |
| 3965122 | bac7dcf | Het Lathiya | docs(spec): IMD-119 record the generation id in the in-progress error |
| 566259b | 37b3f18 | Het Lathiya | test(generation): IMD-119 in-progress conflict carries the active generation id |
| 3ef6aac | ceef6c1 | Het Lathiya | fix(generation): IMD-119 name the active generation in the in-progress conflict |
| 7b7fe81 | 85186d5 | Manasvi Rathore | docs: IMD-118 screens follow the UI design guide |
| 76be0b8 | 4466ed8 | Manasvi Rathore | docs(spec): IMD-118 record the UI design guide decision |
| fd7f9d7 | c0e5a8d | Manasvi Rathore | style(web): IMD-118 theme tokens and Inter typeface |
| 5022d6a | 2a337f8 | Manasvi Rathore | docs(guides): IMD-118 UI design guide |
| 10095e5 | 3b6dcc8 | Het Lathiya | docs(progress): IMP-211 add whole-task part record |
| 6d05efa | 485a041 | Het Lathiya | test(itinerary): IMP-211 itinerary read and latest lookup tests |
| 57a3212 | 4d548f0 | Het Lathiya | test(authz): IMP-211 add the itinerary read routes to the route matrix |
| 7b6bd58 | 42e5bc8 | Het Lathiya | feat(itinerary): IMP-211 latest itinerary lookup for the caller |
| 0df2bc5 | 1f22714 | Het Lathiya | feat(itinerary): IMP-211 read the saved itinerary with days and items in two queries |
| 42ed3fa | 95c3342 | Manasvi Rathore | docs(progress): IMP-212 add whole-task part record |
| 886b43f | bd54aa5 | Manasvi Rathore | test(e2e): IMP-212 create a trip end to end |
| 7c74f44 | 878122c | Manasvi Rathore | test(web): IMP-212 trip wizard component tests |
| ffaf688 | 52fecf5 | Manasvi Rathore | feat(web): IMP-212 four-step trip wizard with per-step saving |
| 1edd19b | 1a0c168 | Manasvi Rathore | feat(web): IMP-212 preference form with field effects and must-visit picker |
| 275ca96 | 434554f | Manasvi Rathore | feat(web): IMP-212 trip and preference validation mirroring the server rules |
| b4af4d0 | adcccf6 | Manasvi Rathore | docs(guides): IMD-117 screen-draft and porting guide |
| 974d4a2 | 1ee743d | Manasvi Rathore | docs: IMD-117 add the screen-draft rule to CLAUDE.md |
| 0999609 | 1177d9c | Manasvi Rathore | docs(spec): IMD-117 record screen drafts as design references |
| b125a60 | fcbf810 | Mohammad Junaid Kureshi | docs(progress): IMP-215 add whole-task part record |
| ebb744d | 334753b | Mohammad Junaid Kureshi | docs(guides): IMP-215 how to add a route to the authorization suite |
| 18332f0 | 9655ce0 | Mohammad Junaid Kureshi | test(authz): IMP-215 two-user ownership suite with no-change checks on writes |
| 14d87d5 | d6b4c91 | Mohammad Junaid Kureshi | test(authz): IMP-215 route matrix for every implemented owned route |
| 106aa59 | debb491 | Het Lathiya | docs(progress): IMP-210 add whole-task part record |
| 5b90109 | edd68e4 | Het Lathiya | test(generation): IMP-210 generation start, poll and save tests |
| c170a35 | 3dd4f61 | Het Lathiya | feat(generation): IMP-210 start and poll a generation job with idempotency and in-progress conflict |
| 4e9c954 | 497eba0 | Het Lathiya | feat(generation): IMP-210 minimal MOCK pipeline with io-1 and place-ID checks |
| 5c5b3c8 | d42e2aa | Het Lathiya | feat(itinerary): IMP-210 save days, items, version and completed record in one transaction |
| 10748fb | 9e7c8a0 | chaudhari kirtan sandipbhai | docs(progress): IMP-201 add whole-task part record |
| d991312 | f433430 | chaudhari kirtan sandipbhai | test(core): IMP-201 readiness, log line and log-scan redaction tests |
| fd2db3f | aaf7d8c | chaudhari kirtan sandipbhai | feat(core): IMP-201 one access log line per request with request id and latency |
| 7c59e2d | 4548a09 | chaudhari kirtan sandipbhai | feat(core): IMP-201 JSON request logging with redaction filter |
| 10e86ed | aa550e3 | chaudhari kirtan sandipbhai | feat(core): IMP-201 readiness endpoint with database, migration and provider checks |
| d2cfbe2 | 57b0fd9 | Het Lathiya | docs(progress): IMP-219 add whole-task part record |
| 75f2835 | df4ab7e | Het Lathiya | test(auth): IMP-219 auth stub bootstrap and user row mirroring tests |
| 091893a | 1b456f8 | Het Lathiya | build: IMP-219 make db-bootstrap and DB_AUTH_STUB in .env.example |
| 30c4455 | c04cf15 | Het Lathiya | feat(db): IMP-219 operator delete-user command for stub databases |
| 8338e17 | 68dadff | Het Lathiya | feat(auth): IMP-219 mirror the auth user row before the profile when DB_AUTH_STUB is on |
| 5879acf | 6310e20 | Het Lathiya | feat(db): IMP-219 apply the auth stub when the auth schema is missing |
| 2053abf | 474e32e | Malhar Mer | docs(progress): IMP-311 add whole-task part record |
| 0dbee5a | 6738524 | Malhar Mer | test(db): IMP-311 RAG store constraints, cosine query and privileges |
| af3b1f3 | 1ecf580 | Malhar Mer | build(db): IMP-311 pgvector test database image in compose and CI |
| 9dda6cc | 4b6c899 | Malhar Mer | feat(db): IMP-311 ORM models for the RAG store, item citations and retrieval record |
| 68e1989 | 9ad3235 | Malhar Mer | feat(db): IMP-311 migration 0007_rag_store with pgvector, corpus and chunk tables |
| 1baa1f0 | fa4dd19 | chaudhari kirtan sandipbhai | docs(progress): IMP-214 add whole-task part record |
| 836e9f0 | 2f0764d | chaudhari kirtan sandipbhai | test(contract): IMP-214 contract test for the MVP endpoint set |
| e339b52 | 87d4450 | chaudhari kirtan sandipbhai | ci: IMP-214 run make openapi-check in lint-types |
| aac10f0 | 00b67cd | chaudhari kirtan sandipbhai | feat(web): IMP-214 generated types and openapi-fetch client with error envelope |
| 88d6fdc | f5cec79 | chaudhari kirtan sandipbhai | build(api): IMP-214 openapi export and contract v1 with the AI schemas |
| a090b58 | 9f60ff2 | chaudhari kirtan sandipbhai | feat(api): IMP-214 SourceRef on itinerary items and retrieval fields on GenerationOut (A1) |
| 1b563c6 | b2e23cc | chaudhari kirtan sandipbhai | feat(api): IMP-214 declare every MVP endpoint with 501 placeholders for unbuilt routes |
| 78629b9 | 6e79316 | Mohammad Junaid Kureshi | docs(progress): IMP-209 record removal of a stray commit before review |
| 384afa0 | 526a5f6 | Mohammad Junaid Kureshi | docs(progress): IMP-209 add whole-task part record |
| 460a20a | 57d7346 | Mohammad Junaid Kureshi | test(routing): IMP-209 estimate, rounding and buffer tests |
| c4328d6 | 85501f5 | Mohammad Junaid Kureshi | build(api): IMP-209 pure-domain import contract for the routing estimate |
| b699410 | 71a5a34 | Mohammad Junaid Kureshi | feat(routing): IMP-209 routing service returning the fallback estimate |
| 464a435 | 7896b3e | Mohammad Junaid Kureshi | feat(routing): IMP-209 pure distance-based travel-time estimate and buffers |
| 2c0ef51 | dc19164 | chaudhari kirtan sandipbhai | docs(progress): IMD-114 add board issues for the A1 cards |
| 2fa61ec | 1e8375b | chaudhari kirtan sandipbhai | docs: IMD-99 update CLAUDE.md for AWS hosting and the RAG pipeline |
| fdf2643 | 83810c1 | chaudhari kirtan sandipbhai | docs(spec): IMD-99 update the sprint guide, traceability matrix and planner prompt for A1 |
| 5c53db1 | 1e98f4a | chaudhari kirtan sandipbhai | docs(spec): IMD-114 add the A1 task cards and amend the affected cards |
| 361b9d6 | 77bbf8b | chaudhari kirtan sandipbhai | docs(spec): IMD-99 record decisions IMD-99 to IMD-116 |
| 8c0204e | 3b4bfc4 | chaudhari kirtan sandipbhai | docs(spec): IMD-99 add Amendment A1 for AWS hosting and the RAG pipeline |
| a740518 | f746076 | Nidhi Chauhan | docs(progress): IMP-208 add whole-task part record |
| e7c1335 | 2b60608 | Nidhi Chauhan | test(ai): IMP-208 factory selection, refusal and isolation tests |
| 15f3041 | 5a4ce4d | Nidhi Chauhan | feat(core): IMP-208 resolve the provider and prompt template at start-up |
| 5074b4f | e01da39 | Nidhi Chauhan | feat(ai): IMP-208 provider factory selected by AI_PROVIDER |
| d552fe0 | 8dfdc45 | Jeel Fefar | docs(progress): IMP-202 add whole-task part record |
| 41cad94 | 2856885 | Jeel Fefar | test(generation): IMP-202 generation record lifecycle, usage and privacy tests |
| ba23e58 | 5fafb3e | Jeel Fefar | feat(generation): IMP-202 owner-scoped generation record repository |
| 081e7ce | 7f37b5e | Jeel Fefar | feat(generation): IMP-202 generation status machine and record helpers |
| bbaa573 | 6388678 | Manya Rana | docs(progress): IMP-207 add whole-task part record |
| dde425c | 436480a | Manya Rana | test(ai): IMP-207 mock provider unit tests and contract registration |
| dda9977 | d81fd49 | Manya Rana | feat(ai): IMP-207 deterministic mock provider with scenarios honoured outside production |
| b0cfdc1 | bed967d | Manal Patel | docs(progress): IMP-204 add whole-task part record |
| 7fc09f4 | dc7226c | Manal Patel | test(trips): IMP-204 preference API and mapping tests |
| d3cfdfc | 3f38dc8 | Manal Patel | feat(trips): IMP-204 read preferences with per-field effects |
| 16ea9b3 | 92bad0c | Manal Patel | feat(trips): IMP-204 save preferences and must-visit places in one transaction |
| 31fd1d5 | 6e8b648 | Manal Patel | feat(trips): IMP-204 preference schemas and pure mapping pm-1 to filters and weights |
| c425fb1 | 52ce7f6 | Jeel Fefar | docs(progress): IMP-205 record the service layer fix in the places-api-search record |
| b2ada13 | 918cda8 | Jeel Fefar | refactor(places): IMP-205 route destinations and place search through a places service |
| 02d216f | b266b87 | Jeel Fefar | docs(progress): IMP-205 add places-api-search part record |
| bffb587 | 0638430 | Jeel Fefar | test(places): IMP-205 destinations and place search API tests |
| 7ae6abc | 052b08a | Jeel Fefar | feat(places): IMP-205 basic place search for the must-visit picker |
| 1a467a8 | 289c2de | Jeel Fefar | feat(places): IMP-205 places repository and destinations endpoint |
| 82cfe0b | a6096e1 | Malhar Mer | docs(progress): IMP-205 add import-quality-gate part record |
| 60fc616 | 8cc7658 | Malhar Mer | test(places): IMP-205 quality gate and import integration tests |
| 89bdda6 | 4b8d2cd | Malhar Mer | ci(places): IMP-205 run the quality gate in check mode in CI |
| 1b9fbca | 05ae40f | Malhar Mer | feat(places): IMP-205 provenance-preserving import pipeline with quality report |
| 4fa9eb6 | 8500b16 | Malhar Mer | fix(places): IMP-205 give the SAMPLE fixture source its retrieved date |
| b8c112a | 7d044db | Malhar Mer | feat(places): IMP-205 quality gate with reject and flag reasons |
| 1d943dd | 079720a | Malhar Mer | feat(places): IMP-205 shared category, tag and suitability vocabulary |
| cc6a900 | e94303d | Manal Patel | docs(progress): IMP-203 record the currency rule fix in the part record |
| 2e923e0 | 084dd06 | Manal Patel | fix(trips): IMP-203 require the budget currency to match the destination currency |
| a8e4f68 | 84ffe37 | Manal Patel | docs(progress): IMP-203 add whole-task part record |
| e2257e8 | d754b5c | Manal Patel | test(trips): IMP-203 trip validation, ownership and pagination tests |
| f3c76d6 | 6201206 | Manal Patel | feat(trips): IMP-203 create, list and read trip endpoints |
| 31a5c02 | 9b0377e | Manal Patel | feat(trips): IMP-203 owner-scoped trip repository and default budget settings |
| 51b15b3 | 086a157 | Manal Patel | feat(trips): IMP-203 trip schemas and pure validation rules |
| eb44ee3 | a72b1bc | chaudhari kirtan sandipbhai | docs(progress): IMP-199 add whole-task part record |
| 040f020 | 2bf5b82 | chaudhari kirtan sandipbhai | docs(progress): IMP-199 record gate SG-1 result, audit and carry-over list |
| 1699ab3 | 1f0d7ec | chaudhari kirtan sandipbhai | docs(guides): IMP-199 contributing guide for one pull request per card and the working agreement |
| c92eb62 | 38fa3b0 | chaudhari kirtan sandipbhai | docs(decisions): IMP-199 record team decisions IMD-64 to IMD-68 and accepted implementation choices |
| 5eeb281 | b2bb1cf | chaudhari kirtan sandipbhai | docs(progress): IMP-199 compile the sprint 1 index from the part records |
| 887e25e | e52de37 | Nidhi Chauhan | docs(progress): IMP-113 add gemini-key-terms part record |
| 391e44c | 6cd781f | Nidhi Chauhan | docs(accounts): IMP-113 Gemini tier, terms and model ID section |
| 263832d | 8594bc0 | Mohammad Junaid Kureshi | docs(progress): IMP-113 add ors-email-sender part record |
| a7a170e | cbd43d6 | Mohammad Junaid Kureshi | docs(accounts): IMP-113 OpenRouteService and email confirmation sections |
| c07d6e6 | 9db373f | chaudhari kirtan sandipbhai | docs(progress): IMP-113 add accounts-secrets-register part record |
| aeb74c6 | 7892197 | chaudhari kirtan sandipbhai | docs(accounts): IMP-113 accounts register template and secrets register rows |
| 4764c5f | b9fcb9f | chaudhari kirtan sandipbhai | docs(progress): IMP-112 add whole-task part record |
| 970ae88 | eadd84c | chaudhari kirtan sandipbhai | docs(guides): IMP-112 deployment guide with the hosted steps blocked by IMP-113 |
| 16edb29 | ea50db4 | chaudhari kirtan sandipbhai | ci(deploy): IMP-112 staging and production deploy workflows that skip until configured |
| 2366433 | 2743620 | chaudhari kirtan sandipbhai | test(api): IMP-112 deployed smoke test and make smoke target |
| bcc45c7 | 59ef721 | chaudhari kirtan sandipbhai | build(api): IMP-112 production Dockerfile with non-root user and no start-up migrations |
| daeb8e0 | 4d350f5 | Manya Rana | docs(progress): IMP-111 add whole-task part record |
| 0bd1d03 | 3c84288 | Manya Rana | test(ai): IMP-111 registry lookup, rendering and template hash tests |
| e9614ae | bb6aadd | Manya Rana | feat(ai): IMP-111 prompt-template registry with version lookup and hashes |
| a538504 | 3d688bc | Manya Rana | feat(ai): IMP-111 itinerary_generate v1 prompt templates and metadata |
| d05ca5d | d7e1b20 | Jeel Fefar | docs(progress): IMP-107 add whole-task part record |
| c7a86e8 | 3939912 | Jeel Fefar | test(places): IMP-107 seed idempotency, provenance and format-error tests |
| f4521e6 | df950e0 | Jeel Fefar | build(db): IMP-107 make seed and make db-reset run the loader |
| f7c9dc5 | ce15df8 | Jeel Fefar | feat(places): IMP-107 idempotent seed command for fixture directories |
| 9b86b0b | bc1c2ab | Jeel Fefar | feat(places): IMP-107 Sampleton SAMPLE fixture destination files |
| 19d7239 | e00fd18 | Het Lathiya | docs(progress): IMP-108 add whole-task part record |
| 88fbf21 | 85b9d4c | Het Lathiya | test(auth): IMP-108 token, route inventory, ownership and profile tests |
| ae19148 | 13318b4 | Het Lathiya | feat(auth): IMP-108 protect every /api/v1 route and add GET /api/v1/me |
| 92e474f | ca493ad | Het Lathiya | feat(auth): IMP-108 CurrentUser dependency with first-call profile creation |
| 6ef2e0b | 500c852 | Het Lathiya | feat(auth): IMP-108 Supabase token verification with JWKS or HS256 |
| f3653de | 165f5e1 | Nidhi Chauhan | docs(progress): IMP-110 add whole-task part record |
| b0fc796 | 33a61db | Nidhi Chauhan | test(ai): IMP-110 schema, error and provider contract tests |
| 1ff3941 | a0c4202 | Nidhi Chauhan | build(ai): IMP-110 export the AI JSON Schemas through make openapi |
| 65ea7db | f452753 | Nidhi Chauhan | feat(ai): IMP-110 ModelProvider protocol and Stage 2 fine-tuned stub |
| e29f628 | 53bb54a | Nidhi Chauhan | feat(ai): IMP-110 provider error hierarchy with retryable flags and failure reasons |
| b5a97cc | 4694e1d | Nidhi Chauhan | feat(ai): IMP-110 gr-1 and io-1 schemas with ProviderResult and metadata types |
| 7c9f5f4 | 2aaf081 | Krrish Kamani | docs(progress): IMP-109 record the smoke spec fix in the part record |
| ca2b158 | 798048f | Krrish Kamani | test(web): IMP-109 sign in before the dashboard viewport checks in the smoke spec |
| 50160f0 | b7cde13 | Krrish Kamani | docs(progress): IMP-109 add whole-task part record and sign-up screenshot |
| 22e04e7 | 32daf48 | Krrish Kamani | test(auth): IMP-109 AuthGuard unit test and auth end-to-end spec with local users |
| 3872708 | 8339d9e | Krrish Kamani | fix(auth): IMP-109 stream the auth forms behind Suspense under cacheComponents |
| 03dcdd2 | 6d4e1b2 | Krrish Kamani | feat(auth): IMP-109 AuthGuard on the app layout with sign-out that clears the cache |
| e2b44ff | c142220 | Krrish Kamani | feat(auth): IMP-109 sign-up and sign-in screens with field validation |
| af155a1 | a9db38c | Krrish Kamani | feat(auth): IMP-109 auth callback route and safe next redirect |
| 057dc40 | e3e089b | Krrish Kamani | feat(auth): IMP-109 browser Supabase client and session hook |
| 99c7510 | 44ffd3e | Jeel Fefar | docs(progress): IMP-106 add orm-drift-fixture part record |
| 4742d60 | 3d565e9 | Jeel Fefar | test(db): IMP-106 test database fixture, schema drift and RLS tests |
| 023595b | 00859e0 | Jeel Fefar | feat(db): IMP-106 typed ORM models for the 15 MVP tables |
| 659d4aa | fdc88ad | Jeel Fefar | feat(db): IMP-106 async session factory and transaction helper |
| 582ba20 | 1ec0b78 | Malhar Mer | docs(progress): IMP-106 add sql-migrations part record |
| 18b1cff | 524e0d4 | Malhar Mer | ci(db): IMP-106 make db-migrate and the CI api job run the migrations |
| 19d1d73 | 6e3487b | Malhar Mer | feat(db): IMP-106 Alembic environment and revisions 0001 to 0006 |
| 6adb4bc | ec2a8ef | Malhar Mer | feat(db): IMP-106 copy MVP migration SQL and auth stub from Appendix A |
| db02416 | 5c0743b | Manasvi Rathore | docs(progress): IMP-104 add whole-task part record and screenshots |
| a372a5b | 1e98779 | Manasvi Rathore | chore(web): IMP-104 track the env.local template from IMP-105 |
| 6480dd5 | ede9740 | Manasvi Rathore | test(web): IMP-104 Vitest and Playwright setup with AppShell and viewport tests |
| efd0787 | 3ecd4a9 | Manasvi Rathore | feat(web): IMP-104 state components, landing page and dashboard placeholder |
| dc46763 | e401253 | Manasvi Rathore | feat(web): IMP-104 query provider, query-key factory and feature flags |
| d614ca0 | 3961f3e | Manasvi Rathore | feat(web): IMP-104 responsive AppShell with skip link and phone navigation |
| 83c65bf | e578e0d | Manasvi Rathore | feat(web): IMP-104 initialise shadcn/ui primitives and design tokens |
| a4868a7 | 6ac5590 | Malhar Mer | docs(progress): IMP-105 add whole-task part record |
| 3f09855 | bbc40ef | Malhar Mer | docs(guides): IMP-105 add local setup guide and secrets register |
| 3b20ff3 | 3739191 | Malhar Mer | ci(github): IMP-105 fail CI when a real env file is tracked |
| dffb2c2 | 5dfa208 | Malhar Mer | chore(build): IMP-105 make stack and db targets run the local services |
| 31bc173 | 5e780ab | Malhar Mer | chore(env): IMP-105 add placeholder-only env templates |
| 7dafe30 | 3e49af6 | Malhar Mer | chore(env): IMP-105 add docker compose db and api services |
| c38086d | f798e1a | Malhar Mer | chore(env): IMP-105 add Supabase local stack config |
| a54493f | f2c8866 | Manal Patel | docs(progress): IMP-103 add whole-task part record |
| 43ce9e8 | 3b6cf8e | Manal Patel | test(core): IMP-103 start-up rule, error envelope and health API tests |
| 49767b5 | 4190719 | Manal Patel | feat(core): IMP-103 app factory with CORS and GET /health |
| a5ee6c3 | b16aa5e | Manal Patel | feat(core): IMP-103 error envelope, domain exceptions and handlers |
| f4c4d39 | 78bfbbd | Manal Patel | feat(core): IMP-103 request id middleware and feature flags |
| df737e8 | 0bbbbc3 | Manal Patel | feat(core): IMP-103 typed settings with start-up checks |
| 8c7d8dd | 70dd95f | chaudhari kirtan sandipbhai | docs(progress): IMP-102 record protection status, red-check runs and board in the part record |
| 7c1a23e | 819e452 | chaudhari kirtan sandipbhai | docs(progress): IMP-102 add issue numbers to the board issue list |
| 3beaac4 | beca578 | chaudhari kirtan sandipbhai | docs(progress): IMP-102 record CI results in the whole-task part record |
| 83a73e7 | f685453 | chaudhari kirtan sandipbhai | docs(progress): IMP-102 add whole-task part record |
| fe3dd12 | 9ec5c7a | chaudhari kirtan sandipbhai | docs(progress): IMP-102 add board issue list for every task part |
| a2441b2 | 5c0305c | chaudhari kirtan sandipbhai | docs(guides): IMP-102 add contributing guide with the team contribution rules |
| a5ae4ac | c29b2fd | chaudhari kirtan sandipbhai | chore(github): IMP-102 add pull request template and CODEOWNERS |
| d20d09d | 25bf58e | chaudhari kirtan sandipbhai | feat(repo): IMP-102 add tracked commit-msg hook and CI attribution check script |
| 6e7944a | b41e272 | chaudhari kirtan sandipbhai | ci(github): IMP-102 add CI workflow with lint-types, unit, guards, attribution, audit and api jobs |
| 4e4a7fe | 32cc77b | Het Lathiya | docs(progress): IMP-101 add api-pyproject-guard part record |
| 466e545 | 320d45a | Het Lathiya | test(api): IMP-101 add provider socket guard and its unit test |
| bbed8a4 | 8284677 | Het Lathiya | build(api): IMP-101 add import-linter layer and vendor isolation contracts |
| e41d971 | 5b24eef | Het Lathiya | build(api): IMP-101 add pyproject with runtime and dev dependencies, ruff, mypy and pytest config |
| 61a3e64 | dd38482 | chaudhari kirtan sandipbhai | docs(progress): IMP-101 add sprint-1 index, gates, part record guide and part record |
| 778a349 | e6f9889 | chaudhari kirtan sandipbhai | chore(web): IMP-101 stop next dev from writing a second instruction file |
| ac89142 | f9eda0d | chaudhari kirtan sandipbhai | chore(repo): IMP-101 add editor, git and pre-commit config, toolchain pins, README and shared settings |
| 1baea9b | 6308f45 | chaudhari kirtan sandipbhai | chore(build): IMP-101 add root Makefile with all section 4.7 targets |
| 2e73f43 | cd341b4 | chaudhari kirtan sandipbhai | chore(web): IMP-101 scaffold Next.js app with scripts and lockfile |
| 41f5486 | 9d0aa5e | chaudhari kirtan sandipbhai | chore(repo): IMP-101 create repository tree with purpose notes |
| 1e251b7 | 1b9ea3b | chaudhari kirtan sandipbhai | chore(docs): IMP-101 commit specification document set and CLAUDE.md unchanged |
| 19072f2 | 6ad568b | chaudhari kirtan sandipbhai | chore: initialize repository |
