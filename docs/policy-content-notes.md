# Policy content notes

The mode-specific knowledge files under `data/sample_policies/` are general explanatory starter material, not official company policy or legal advice. Exact provider-specific fees, deadlines, eligibility rules, baggage allowances, and document requirements can change. Verify them against current official sources before use.

The chatbot must explain procedures only. It must not book, cancel, reschedule, collect payment, claim a transaction happened, or imply live access to availability, booking, PNR, or refund status. Never request passwords, OTPs, card PIN/CVV, full card numbers, or full passport/ID numbers.

Provider-neutral workflow, FAQ, glossary, usage, and source-maintenance references are in `docs/policy-reference/` and are not indexed as provider-specific policy. Keep train knowledge in `railways/`. Put airline-specific knowledge below `data/sample_policies/airways/<airline>/` (`spicejet`, `indigo`, or `air_india`) and bus platform/operator knowledge below `data/sample_policies/bus/<provider>/` (`redbus`, `abhibus`, `makemytrip`, or `apsrtc`). Retrieval filters on these folders so one provider's rules cannot be returned for another. Record official source URLs and review dates when adding provider-specific policy details. Use descriptive filenames such as `cancellation-refunds.txt`; keep each file focused on one topic.

The `00_*_policy_answers.txt` files are concise reference answers for the four common questions. Provider answer files live with their airline or bus platform/operator, so source links match the selected provider. For aggregator platforms such as redBus, AbhiBus, and MakeMyTrip, distinguish platform processes from the bus operator's ticket-specific rules. Other questions must have a recognized policy topic and relevant matching passages from the selected provider; otherwise the chatbot declines them instead of using outside knowledge.

Format every supported response consistently: `Step 1: Short action or check`, followed by one or two brief explanatory lines, then a blank line before the next `Step N:`. Keep steps in practical order and explain any decision the traveller must make. For policy questions that are not a procedure, phrase the steps as checks the traveller should perform. The app displays source links below the answer; include only sources that support the selected provider's guidance. Keep complete actions, avoid splitting semicolon-linked actions, and remove repeated points. Avoid fixed fees, deadlines, baggage allowances, or refund promises unless verified against current official terms. Update these reference answers alongside detailed provider topic files when policies change.

For every new or revised answer, review it in each applicable mode and ask:

- Does every step answer the user's exact question and belong to the selected mode?
- Is each action complete, in a sensible order, and understandable without surrounding paragraphs?
- Are variable fees, deadlines, eligibility, and refund outcomes qualified instead of guessed?
- Does the answer cite only sources that support the included points?
- Would a question outside this database be declined instead of answered from general knowledge?

Do not pad an answer with neighboring passage text just to make it longer. Prefer a short supported answer or a clear database-coverage refusal over a plausible but unsupported instruction.
