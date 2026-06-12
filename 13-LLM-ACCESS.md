# LLM access through YieldFabric — chat for app builders

This guide is for a builder who wants their app to talk to an LLM
**through YieldFabric** instead of holding an OpenAI / Azure key of
their own. The agents service (`agents.yieldfabric.com`, port 3001
in dev) is the access layer: it authenticates your caller, applies
optional RAG grounding from the caller's knowledge graphs, persists
conversation state, streams tokens back over SSE, and meters every
upstream call per entity for billing and audit.

What you get:

- **An OpenAI-compatible endpoint** (`/v1/chat/completions`,
  `/v1/embeddings`, `/v1/models`) — point any OpenAI SDK at YF with
  your `yf_api_…` key as the `api_key` and it works, including
  standard tool calling and the `yf` extension that grounds
  completions in your knowledge substrate and exposes
  server-executed `rag_search` / `start_reasoning` tools.
- **One authenticated chat endpoint** (`POST /chat`) with streaming
  (SSE) and non-streaming (JSON) modes.
- **Per-request model selection** between the deployment's
  configured models (typically `default` and `mini`), plus
  `max_output_tokens` and `temperature` controls; the catalog is
  served at `GET /api/models`.
- **A stateless "pure proxy" mode** — skip RAG, skip intent
  classification, supply your own system prompt and history.
- **Grounded mode** — scope answers to a knowledge graph or a
  working group's documents.
- **Multi-party agent chat** — threads inside working groups where
  named agents reply, with live SSE events.
- **Multi-agent reasoning** — a pipeline that forms a team of
  agents around a problem and streams its progress.
- **Per-entity usage metering** — token counts per call, daily
  rollups, queryable over REST.

What you do **not** get (today): models beyond the deployment's
configured catalog, or multimodal input. See
[Limitations](#limitations-and-operational-notes) before you commit
to a design.

## Choosing a surface

| You want | Use |
|--|--|
| Your existing OpenAI SDK / LangChain / AI-SDK code, unchanged (incl. tool calling) | `/v1/chat/completions` + `/v1/embeddings` with `base_url` pointed at YF |
| RAG / reasoning inside your OpenAI SDK calls | `/v1/chat/completions` + `extra_body={"yf": {working_group_id, kg_id, builtin_tools}}` |
| "ChatGPT in my app" — one user, one assistant, streaming | `POST /chat` with `Accept: text/event-stream` |
| A stateless LLM call (you own prompt + history) | `POST /chat` with `skip_rag: true`, `reasoning: false` (or `/v1/chat/completions`) |
| Answers grounded in the user's documents / KG | `POST /chat` with `kg_id` or `working_group_id` |
| Multi-party chat where named agents participate | Working-group threads + `GET /working-groups/{id}/chat/stream` |
| A team of agents reasoning over a hard problem | `POST /pipelines/run` (`kind: "reasoning"`) + events SSE |
| Token usage for billing / quotas | `GET /api/usage/summary`, `GET /api/usage/detail` |

## Authentication

Same story as the rest of the platform (see
[`building-with-yf.md`](../docs/building-with-yf.md) §"Authenticate in 30
seconds"): browser clients sign in via the auth service and send
`Authorization: Bearer <JWT>`. Backend services can send their
**`yf_api_…` API key directly as the bearer** on any agents endpoint
— the service exchanges it for a JWT server-side (cached), so you
don't need to manage the exchange yourself. Every presented
credential is signature-validated before your request reaches a
handler; forged or expired tokens get a 401.

One transport caveat: the `GET` SSE endpoints
(`/working-groups/{id}/chat/stream`, `/pipelines/{run_id}/events`)
also accept the token as a query parameter —
`?access_token=<JWT>` — because the browser `EventSource` API
cannot set headers. `POST /chat` streams over a regular `fetch`
response body, so the normal `Authorization` header works there.

## Direct chat: `POST /chat`

The canonical single-assistant entry point — the same endpoint
the YieldFabric app's own assistant and embedded terminal use, so
anything you build on it gets the exact behaviour the first-party
UI gets.

### Request body

Field names accept both snake_case and camelCase (serde aliases).

| Field | Type | Meaning |
|--|--|--|
| `message` | string, required | The user's message. |
| `context` | string, default `"chat"` | Free-form label that namespaces persisted history. |
| `thread_id` | string \| null | Conversation thread. Omit to have the server generate one (returned in every response). |
| `conversation_history` | `[{role, content}]` | Prior turns, prepended to the LLM conversation. Use this for stateless calls where you keep history client-side. |
| `system_prompt` | string \| null | Overrides the default assistant system prompt. |
| `reasoning` | bool \| null | `false` = skip intent classification, direct LLM call. `null` (default) lets the classifier decide. Multi-agent reasoning is **not** behind this flag — that's `POST /pipelines/run`. |
| `skip_rag` | bool, default `false` | `true` = no retrieval at all; pure LLM response. |
| `kg_id` | string \| null | Scope RAG retrieval to one knowledge graph. |
| `working_group_id` | string \| null | Ground the chat in a working group's substrate (its notebook KG / documents). |
| `as_agent` | string \| null | Answer **as a named agent persona** (loads that agent's role/focus into the system prompt and attributes the reply to it). This selects a persona, not a model. |
| `model` | string \| null | Which configured chat model serves this request: a registry id (`"default"`, `"mini"`) or the deployment name, case-insensitively. Unknown values are a 400 listing the servable models. Omit for the deployment default. Discover the catalog at `GET /api/models`. |
| `max_output_tokens` | int \| null | Per-request output-token cap (server-clamped to 32 000). Omit to keep each path's default. |
| `temperature` | number \| null | Forwarded verbatim when present; omit for the upstream default. Reasoning-family models that reject explicit temperatures surface the upstream error. |
| `ui_context` | object \| null | Frontend context (current page, builder state, …). App-internal; omit it in your own integrations unless you're reusing the YF terminal package. |

Source of truth: the `ChatRequest` schema on `POST /chat` in the
API reference at `/docs/api/agents`.

### Choosing a model

`GET /api/models` returns the catalog this deployment serves —
typically the default chat deployment, a cheaper `mini` deployment,
and the embeddings model:

```bash
curl https://agents.yieldfabric.com/api/models \
  -H "Authorization: Bearer $TOKEN"
# → { "data": [
#      {"id": "default", "model": "gpt-5.2", "kind": "chat", "aliases": ["gpt-5.2"], "default": true},
#      {"id": "mini", "model": "gpt-5.4-mini", "kind": "chat", "aliases": ["gpt-5.4-mini"], "default": false},
#      {"id": "embedding", "model": "text-embedding-ada-002", "kind": "embedding", "aliases": ["text-embedding-ada-002"], "default": false}
#    ] }
```

Pass an entry's `id` (or any alias) as `model` on `POST /chat` —
`"mini"` is the cheap-and-fast choice for classification, drafts,
and short replies. Use the stable ids (`default` / `mini`) rather
than deployment names; deployment names change between
environments. Usage metering records the actual deployment per
call, so per-model cost reporting works out of the box.

## The OpenAI-compatible endpoint: `/v1`

If you already have code written against the OpenAI API — the
official SDKs, LangChain, the Vercel AI SDK — point it at YF and
keep it unchanged:

```python
from openai import OpenAI

client = OpenAI(
    base_url="https://agents.yieldfabric.com/v1",
    api_key=os.environ["YF_API_KEY"],   # your yf_api_… key, used directly
)

out = client.chat.completions.create(
    model="mini",
    messages=[{"role": "user", "content": "Summarise these terms."}],
    stream=True,
)
for chunk in out:
    print(chunk.choices[0].delta.content or "", end="")
```

Three routes: `POST /v1/chat/completions` (streaming and
non-streaming, plus `response_format: json_schema` for strict
structured output), `POST /v1/embeddings` (single or batch input,
max 256 items), and `GET /v1/models`. Errors — including auth
failures — come back in the OpenAI error envelope, so SDK error
handling works as expected.

The supported subset is deliberate and explicit:

- **Honoured:** `model`, `messages` (string content or text parts;
  `assistant` tool-call turns and `tool`-role results round-trip),
  `stream`, `temperature`, `max_completion_tokens` / `max_tokens`
  (clamped to 32 000), `response_format: json_schema`, `tools`,
  `tool_choice`.
- **Rejected with a clear 400:** the legacy `functions` API,
  `n > 1`, `response_format: json_object` (use `json_schema`), and
  `response_format` combined with `stream` or with tools.
- **Accepted and ignored:** tuning parameters with no provider
  lever (`top_p`, penalties, `seed`, `stop`, `logit_bias`).

**Tool calling** works the standard way: pass `tools`, get back
`tool_calls` with `finish_reason: "tool_calls"`, answer with
`tool`-role messages — LangChain/AI-SDK agent loops run unchanged.
One latency note: tool-involving requests with `stream: true` run
buffered upstream and are re-emitted as chunk frames (a single
`tool_calls` or content delta), trading incremental tokens for
protocol correctness.

### The `yf` extension: your substrate, zero plumbing

The `yf` vendor field (sent through the SDKs' `extra_body`) wires
the knowledge substrate straight into the OpenAI call:

```python
out = client.chat.completions.create(
    model="default",
    messages=[{"role": "user", "content": "What payment schedule did we agree with Acme?"}],
    extra_body={"yf": {
        "working_group_id": WG_ID,          # ground in this workspace
        "kg_id": KG_ID,                     # optional: one KG (e.g. a reasoning result)
        "builtin_tools": ["rag_search"],    # let the model search on demand
    }},
)
print(out.choices[0].message.content)
print(out.model_extra["yf"]["sources"])     # citations
```

- **Auto-grounding** — with `working_group_id` (and optionally
  `kg_id`), the last user message is run through the same hybrid
  retrieval the native workspace chat uses, the evidence is injected
  as context, and citations come back in the response's
  `yf.sources`. Working-group membership is enforced (403).
- **`rag_search` builtin** — instead of always-on grounding, the
  model gets a server-executed search tool and decides when to
  query the substrate. Executed in a bounded loop (max 4 rounds,
  then a forced final answer); activity is reported in
  `yf.tool_activity` and never surfaces as client `tool_calls`.
- **`start_reasoning` builtin** — the model can kick off an async
  multi-agent reasoning run (same access gates as
  `POST /pipelines/run`); the tool result carries `run_id`, `kg_id`,
  and `thread_id`, the run continues in the background, and a later
  call grounded on that `kg_id` chats over its results.
- Builtins compose with your own `tools`: client calls always win a
  round and return to you; builtins execute server-side.

Calls are metered per entity like everything else (feature labels
`compat_chat` / `compat_embed`; builtin loop rounds are summed into
the response's `usage`), so your YF usage reporting covers SDK
traffic too.

## Going deeper: from citation to frame

Everything the `yf` extension returns is backed by the **frame
substrate** — knowledge graphs made of typed frames (nodes), slot
edges, and chunks (passages provenance-linked to frames). Your
citations are doorways into it, and the whole graph is reachable
over the native REST API with the same bearer token.

Each entry in `yf.sources` looks like:

```json
{
  "id": "…",                  // node_key when present, else document_id
  "label": "Acme MSA v3.pdf", // document title
  "node_key": "…",            // KG node this evidence cites (optional)
  "type": "Institution",      // formatted frame-type label
  "description": "…"          // chunk text or node description
}
```

Three hops take you from a citation to the underlying knowledge:

```bash
# 1. What's in this KG? (the kg_id you grounded on / got from a
#    reasoning run)
curl "https://agents.yieldfabric.com/kgs/$KG_ID/summary" \
  -H "Authorization: Bearer $TOKEN"

# 2. The frames themselves — filter by kind/lifecycle, e.g. the
#    claims a reasoning run emitted. Response: { kg_id, count,
#    frames: [{ frame_id, frame_kind, lifecycle, verb, stance,
#    concept_type, label, description, confidence, … }] }
curl "https://agents.yieldfabric.com/kgs/$KG_ID/frames?kind=speech_act&limit=100" \
  -H "Authorization: Bearer $TOKEN"
# Single frame: GET /kgs/$KG_ID/frames/$FRAME_ID

# 3. The evidence passages — every chunk in the KG with its citation
#    links. Each row carries { node_key, chunk_text, excerpt,
#    document_id, doc_title, … }: filter by your citation's node_key
#    to get exactly the passages behind it.
curl "https://agents.yieldfabric.com/kgs/$KG_ID/chunks" \
  -H "Authorization: Bearer $TOKEN"
# Chunk detail + its document + prev/next neighbours:
# GET /chunks/$CHUNK_FRAME_ID
```

Also useful: `GET /kgs/{id}/lexicon` (the vocabulary the KG was
extracted with) and `GET /kgs` (every KG you can see). The full
conceptual model — frames, slots, chunks, the lexicon, consensus —
is in [`agents-and-workspaces.md`](../docs/getting-started/agents-and-workspaces.md)
§Knowledge graphs; the wire reference is `/docs/api/agents`.

## Following a reasoning run end to end

The complete loop, from an OpenAI SDK, with the native API filling
the gaps:

```python
# 1. Kick off — the model starts the run via the builtin tool.
out = client.chat.completions.create(
    model="default",
    messages=[{"role": "user", "content": "Analyse the credit risk in the Acme portfolio."}],
    extra_body={"yf": {"working_group_id": WG_ID,
                       "builtin_tools": ["start_reasoning"]}},
)
# run_id / kg_id / thread_id are in the tool activity:
run = out.model_extra["yf"]["tool_activity"][0]["result"]
```

```bash
# 2a. Follow live (SSE — turn narration, checkpoints, completion):
curl -N "https://agents.yieldfabric.com/pipelines/$RUN_ID/events?access_token=$TOKEN"

# 2b. …or poll. status ∈ running | paused | complete | failed | cancelled;
#     `paused_reason` says which checkpoint, `target_kg_id` is where
#     results land.
curl "https://agents.yieldfabric.com/pipelines/$RUN_ID" \
  -H "Authorization: Bearer $TOKEN"

# 3. If paused at a checkpoint (team formation / vocab review),
#    resume with approval or steering guidance:
curl -X POST "https://agents.yieldfabric.com/pipelines/$RUN_ID/input" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"kind": "proceed"}'        # or {"kind": "guidance", "content": "…"}
```

```python
# 4. status == "complete" → chat over the results by grounding on
#    the run's KG (and explore it via the frame endpoints above).
out = client.chat.completions.create(
    model="default",
    messages=[{"role": "user", "content": "Summarise the team's conclusion and the dissents."}],
    extra_body={"yf": {"working_group_id": WG_ID, "kg_id": run["kg_id"]}},
)
```

The run also writes its narrative into a dedicated `reasoning`
thread (`thread_id` from step 1) — fetch it with
`GET /working-groups/{id}/threads/{tid}/messages` if you want the
agent-by-agent transcript rather than a synthesis.

### Response modes

Content-negotiated on the `Accept` header.

**SSE** (`Accept: text/event-stream`) — a stream of `data:` frames,
each a JSON object:

```json
{"chunk": "Hel", "thread_id": "…", "is_final": false, "sender": {"entity_id": "agent:reasoning", "display_name": "Workspace Assistant", "type": "agent"}}
```

The last frame repeats the **full** response text with
`"is_final": true` and, when RAG ran, a `sources` array of citation
references. Treat the final frame as authoritative; render the
incremental `chunk` values for typing effect only.

**JSON** (no `Accept: text/event-stream`) — a single object:

```json
{"response": "…full assistant reply…", "thread_id": "…"}
```

### Recipe: stateless LLM proxy

You manage history and prompt; YF provides auth + metering + the
upstream model. Nothing is grounded, nothing is classified:

```bash
curl -N https://agents.yieldfabric.com/chat \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{
    "message": "Summarise the attached terms in two sentences.",
    "system_prompt": "You are a concise legal summariser.",
    "conversation_history": [
      {"role": "user", "content": "Here are the terms: ..."},
      {"role": "assistant", "content": "Got it."}
    ],
    "skip_rag": true,
    "reasoning": false
  }'
```

For a request/response call instead of a stream, drop the `Accept`
header and read `{response, thread_id}`.

### Recipe: grounded chat

Scope retrieval to a knowledge graph (e.g. one produced by document
ingestion or a reasoning run):

```bash
curl -N https://agents.yieldfabric.com/chat \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{"message": "What payment schedule did we agree?", "kg_id": "'$KG_ID'"}'
```

Or pass `working_group_id` to ground in a workspace's substrate.
The final SSE frame carries `sources` with the citations.

### History and persistence — read this before relying on it

`/chat` persistence is **path-dependent**:

- The default paths (intent-classified SSE, and the JSON mode) run
  through the workflow executor's conversation memory and persist
  turns into the `conversation_history` store, keyed by
  `thread_id` + `context`. `GET /chat/history/{thread_id}` reads
  exactly this store:

  ```bash
  curl "https://agents.yieldfabric.com/chat/history/$THREAD_ID?limit=100" \
    -H "Authorization: Bearer $TOKEN"
  # → { "thread_id": "…", "messages": [{"role", "content", "created_at"}, …] }
  ```

- The **workspace mode** (request has a `working_group_id`, no
  `system_prompt`, no page context) persists into the
  working-group **thread message** store instead — read it back
  with `GET /working-groups/{id}/threads/{tid}/messages`, not
  `/chat/history`.

If your app needs history it fully controls, the robust pattern is
the stateless one: keep turns client-side (or in your own DB) and
send them back via `conversation_history` on each call. If you
want server-side durable multi-party history, use working-group
threads (next section). `/chat/history` is best treated as what it
is in the YF app: a session-restore convenience for the floating
assistant.

## Multi-party chat: working-group threads

When the conversation has more than one human, or you want named
agents (with tools and memory) participating rather than a bare
assistant, use working-group threads. The model — groups, members,
thread kinds, the privacy rules — is covered in
[`agents-and-workspaces.md`](../docs/getting-started/agents-and-workspaces.md); the wire
surface is:

| Endpoint | What |
|--|--|
| `POST /working-groups/{id}/chat` | Get-or-create the group's team-chat thread. |
| `GET /working-groups/{id}/chat/stream` | SSE: every live event in the group (also accepts `?access_token=`). |
| `POST /working-groups/{id}/threads` | Create a topic thread: `{"title", "thread_type", "reference_id"}`. |
| `GET /working-groups/{id}/threads` | List threads. |
| `POST /working-groups/{id}/threads/{tid}/messages` | Post: `{"content", "msg_references"}`. Mentioning an agent in `msg_references` routes the message to it. |
| `GET /working-groups/{id}/threads/{tid}/messages?limit=&before=` | Paginated history (cursor on `before`). |
| `POST /working-groups/{id}/threads/{tid}/typing` | Typing indicator. |
| `POST /working-groups/{id}/threads/{tid}/read` | Read receipt. |
| `POST /dm` / `GET /dm/conversations` | 1:1 DM groups. |

The flow is **post over REST, receive over SSE**: posting returns
the persisted message; agent replies arrive on the group stream as
`AgentTyping` → `AgentToken` (per-token) → `AgentDone` →
`NewMessage` (the persisted reply). The stream multiplexes the
whole group — filter client-side by `thread_id`. Other event types
on the same stream (`HumanTyping`, `PresenceUpdate`,
`ReadReceipt`, `WorkflowUpdate`, `IntentProposed`, …) are
enumerated in the agents API reference at `/docs/api/agents`
(threads + streaming guides).

This is exactly how the YF app's workspace chat works. For a
production-grade SSE consumer: reconnect with exponential backoff,
and on reconnect refetch the thread's recent messages over REST to
catch anything missed while the stream was down.

## Multi-agent reasoning: `POST /pipelines/run`

For "have a team of agents work this problem" rather than chat.
Two-step protocol (this is what the terminal's **Reason** toggle
does):

```bash
# 1. Start the run
curl -X POST https://agents.yieldfabric.com/pipelines/run \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{
    "kind": "reasoning",
    "name": "Compare repo structures",
    "problem": "Compare the two proposed repo structures and recommend one.",
    "working_group_id": "'$GROUP_ID'",
    "require_team_formation": true,
    "max_turns": 15
  }'
# → { "run_id": "…", "kg_id": "…", "thread_id": "…" }

# 2. Stream progress
curl -N "https://agents.yieldfabric.com/pipelines/$RUN_ID/events?access_token=$TOKEN"
```

Key events: `turn_started`, `transform_extension` with
`kind: "narrative_text"` (prose to show the user),
`pipeline_checkpoint` (the run **pauses** — resume with
`POST /pipelines/{run_id}/input` body `{"kind": "proceed"}` or
`{"kind": "guidance", "content": "…"}`), `pipeline_complete`,
`pipeline_failed`. `POST /pipelines/{run_id}/cancel` aborts. The
result is a knowledge graph (`kg_id`) you can then chat against via
`POST /chat` + `kg_id`, and a dedicated `reasoning` thread for
follow-up Q&A.

## Usage metering

Every upstream LLM call — chat, agent replies, embeddings, KG
extraction — emits a usage event with the caller's entity id (from
the JWT), the feature label, model, prompt/completion token counts,
latency, and success/error. Two read endpoints:

```bash
# Daily rollups (llm_usage_daily)
curl "https://agents.yieldfabric.com/api/usage/summary?entity_id=$ENTITY&start_date=2026-06-01&end_date=2026-06-12" \
  -H "Authorization: Bearer $TOKEN"

# Raw per-call events (llm_usage)
curl "https://agents.yieldfabric.com/api/usage/detail?feature=chat&limit=100" \
  -H "Authorization: Bearer $TOKEN"
```

Filters: `entity_id`, `working_group_id`, `economy_id`, `feature`,
`model` (+ `request_id`, `thread_id`, `limit`, `offset` on detail).
Summary rows carry `call_count`, `total_prompt_tokens`,
`total_completion_tokens`, `total_tokens` per
`(date, entity, group, economy, feature, model)`.

**Per-message costs**: chat calls are stamped with their
conversation `thread_id`, and every LLM call made while answering
one message (intent classification, retrieval, the completion
itself) shares a `request_id`. So
`GET /api/usage/detail?thread_id=…` grouped by `request_id` gives
one row per user message, with the per-call breakdown inside —
exactly what a token-usage UI needs. The open-source
`examples/yieldfabric-chat` reference app ships a usage drawer
built this way.

> Scoping: staff roles (SuperAdmin/Admin/Manager/Operator) and
> service tokens may filter arbitrarily, including the org-wide
> no-filter view. Everyone else is pinned to their own entity —
> omitting `entity_id` scopes to self, and naming another entity
> returns 403. Safe to build end-user quota UI on directly.

## Limitations and operational notes

Things to know before you design against this surface:

- **Model choice is bounded by the deployment's catalog.** `model`
  selects between the deployments this agents instance is configured
  with (`GET /api/models` — typically `default` and `mini`); it is
  not an open model menu. `as_agent` changes the persona/system
  prompt, never the model.
- **Sampling knobs are minimal.** `max_output_tokens` /
  `max_completion_tokens` and `temperature`; `top_p` and friends are
  not forwarded. The current GPT-5-family deployments reject
  explicit temperatures — expect that to surface as an upstream
  error if you send one.
- **Tool calling is buffered when streaming.** Requests involving
  `tools` (client or `yf` builtins) with `stream: true` complete
  upstream first, then stream synthesized chunk frames — correct
  protocol, no incremental tokens. Tool calling is also unavailable
  on the Azure serverless (Responses API) backend — it returns an
  explicit error; the deployed classic backend supports it.
- **Upstream providers are OpenAI-family only** — official OpenAI,
  Azure OpenAI classic deployments, and Azure serverless
  (Models-as-a-Service). No Anthropic/other backends are wired
  today.
- **Streaming is SSE only.** No WebSockets; no
  resume-from-event-id. On reconnect, refetch state over REST
  (thread messages, pipeline status) and re-open the stream.
- **Every presented credential is signature-validated** by the
  service itself (a middleware in front of the whole REST
  surface). The
  hermetic-dev kill-switch `AGENTS_JWT_VALIDATION=off` restores the
  old peek-decode behaviour — never run production with it set.
- **Usage endpoints are entity-scoped.** Non-staff callers see only
  their own rows on `GET /api/usage/*`; staff roles
  (SuperAdmin/Admin/Manager/Operator) and service tokens can query
  org-wide. You can now build end-user quota UI directly on them.
- **`/chat` history is path-dependent** (see
  [above](#history-and-persistence--read-this-before-relying-on-it)).
  Prefer client-held `conversation_history` or working-group
  threads.

## See also

- [`building-with-yf.md`](../docs/building-with-yf.md) — auth flows,
  service URLs, the financial-side recipes.
- [`agents-and-workspaces.md`](../docs/getting-started/agents-and-workspaces.md) — the
  conceptual model: workspaces, threads, agents, KGs, pipelines.
- [`webhooks-and-events.md`](../docs/getting-started/webhooks-and-events.md) — the full
  event surface across services.
- `/docs/api/agents` on the running docs site — every agents
  endpoint (~229) with per-operation request/response detail.
