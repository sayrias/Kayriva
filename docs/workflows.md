# Tasks, documents and live progress

## Research without unbounded waits

Research submits up to three searches concurrently rather than queuing every possible query at once. Query phases have time budgets of 15 seconds (quick), 35 seconds (detailed) and 60 seconds (deep); page reading has separate 35/75 second budgets. Three consecutive provider failures stop new submissions. Already collected sources remain available. A target source count is an upper bound, not a promise that every site can be reached.

These budgets cover research orchestration, not model inference. Model loading, prompt evaluation and token generation still depend on the selected model, runtime, memory placement and hardware. Keeping a model loaded saves loading time; it does not make computation instant.

## Stop and resume

Stop uses the send button's location. Partial output, source context, plan and confirmed tool outcomes are saved with the conversation. Use **Resume task**, or send **Continue the interrupted task from where you stopped.**, in the same project.

A bounded checkpoint retains the original request, completed file paths/hashes and pending tool descriptions. The next model turn receives this progress and instructions to inspect existing files before changing them. Tools are not blindly replayed. Changing projects prevents restoration of the other project's checkpoint. External operations whose result was not received are marked uncertain; stopping a wait does not undo an external action.

Checkpoint recovery requires saved progress from this version. It cannot recover an old unsaved result or guarantee that a model will always follow its instructions correctly.

## Better project documents

Document instructions ask for a summary, explanatory sections, concrete examples, version distinctions and linked sources. Long documents are written in meaningful create/append sections so completed parts survive interruption. Successful large file-write arguments are kept in history but compacted in subsequent inference requests to avoid processing the entire report repeatedly.

The model still determines the document's contents. Source collection and formatting instructions are not a factual correctness guarantee. Review important technical claims against the linked sources.

Open a saved text or Markdown file in **Project files** and select **Preview**. The preview does not modify the editor. The prompt library includes document-writing and document-to-plan starting points.

## Composer and attachments

The composer grows with wrapped text, then scrolls at a bounded height. Paste an image, paste local file URLs, drop files, or use the attachment picker. Attached files appear above the input and can be removed individually. An image pasted from the clipboard is prepared in private local storage; actual image interpretation requires a supported vision model and matching projector.

## Real operation details

The live history stays expanded while work is running. Expand an actual tool event to inspect bounded arguments and its result. Known credential fields are redacted in that display. Waiting time updates the current stage instead of adding a new preparation row every few seconds. These are reported operations, not the model's private reasoning.

MCP connection and tool waits have 20/90 second limits. A broken server does not remove healthy servers from the model's tool list. Enabled connections, approval preferences and offline mode still govern which tools may run.

## Skills and application connections

The library has MCP, Apps and Skills tabs. Apps are supported product connections using the same MCP configuration, not transferred accounts from another program. Service credentials, environment requirements and available permissions must be configured for each provider. This client does not supply a general browser OAuth sign-in flow.

Eight original bundled guides cover research, documents, code review, planning, interface design, data analysis, debugging and writing. Guides are selected narrowly for the task, or requested with `$skill-id`. At most two different guides are read per turn; enabling every guide does not load every guide. A real guide read produces a named usage event. A skill gives the model instructions; it does not add a model, network privilege, renderer or terminal.

Import your chosen `SKILL.md` or skill folder under Skills. Only bounded text guide resources are imported; scripts are not executed. Review the imported text and any missing resource notice. Enabled/disabled preferences persist locally. Imported guides can be removed from the library without deleting the original source folder.

Public progress uses actual, request-specific assistant messages without a canned opening paragraph or an extra model call just to narrate. Actual assistant updates and verified tool events are shown in sequence; operation groups expand into individual tools and bounded arguments/results. Older resume buttons disappear as soon as the conversation moves on.
