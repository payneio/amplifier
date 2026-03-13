"""Event vocabulary for the Amplifier kernel.

What's here and why:
  The event NAMES are the contract. Modules emit and subscribe to these
  strings. Having a canonical vocabulary means a logging hook and a
  metrics hook can both subscribe to PROVIDER_RETRY without coordinating
  with each other — they just agree on the string.

  This is the kind of thing that seems trivially replaceable ("just use
  string literals") until you have 15 modules from different authors
  and one of them typos "provider:rety". The vocabulary IS the value.

What's NOT here:
  Any implementation. These are just strings. The original amplifier-core
  re-exports these from a Rust binary — that's unnecessary complexity for
  what amounts to a constants file.
"""

# --- Session lifecycle ---
SESSION_START = "session:start"
SESSION_END = "session:end"
SESSION_FORK = "session:fork"
SESSION_RESUME = "session:resume"

# --- Prompt lifecycle ---
PROMPT_SUBMIT = "prompt:submit"
PROMPT_COMPLETE = "prompt:complete"

# --- Planning ---
PLAN_START = "plan:start"
PLAN_END = "plan:end"

# --- Provider calls ---
PROVIDER_REQUEST = "provider:request"
PROVIDER_RESPONSE = "provider:response"
PROVIDER_RETRY = "provider:retry"
PROVIDER_ERROR = "provider:error"
PROVIDER_THROTTLE = "provider:throttle"
PROVIDER_TOOL_SEQUENCE_REPAIRED = "provider:tool_sequence_repaired"
PROVIDER_RESOLVE = "provider:resolve"

# --- LLM events ---
LLM_REQUEST = "llm:request"
LLM_RESPONSE = "llm:response"

# --- Streaming content blocks ---
CONTENT_BLOCK_START = "content_block:start"
CONTENT_BLOCK_DELTA = "content_block:delta"
CONTENT_BLOCK_END = "content_block:end"

# --- Thinking events ---
THINKING_DELTA = "thinking:delta"
THINKING_FINAL = "thinking:final"

# --- Tool invocations ---
TOOL_PRE = "tool:pre"
TOOL_POST = "tool:post"
TOOL_ERROR = "tool:error"

# --- Context management ---
CONTEXT_PRE_COMPACT = "context:pre_compact"
CONTEXT_POST_COMPACT = "context:post_compact"
CONTEXT_COMPACTION = "context:compaction"
CONTEXT_INCLUDE = "context:include"

# --- Orchestrator lifecycle ---
ORCHESTRATOR_COMPLETE = "orchestrator:complete"
EXECUTION_START = "execution:start"
EXECUTION_END = "execution:end"

# --- User notifications ---
USER_NOTIFICATION = "user:notification"

# --- Artifacts ---
ARTIFACT_WRITE = "artifact:write"
ARTIFACT_READ = "artifact:read"

# --- Policy / approvals ---
POLICY_VIOLATION = "policy:violation"
APPROVAL_REQUIRED = "approval:required"
APPROVAL_GRANTED = "approval:granted"
APPROVAL_DENIED = "approval:denied"

# --- Cancellation ---
CANCEL_REQUESTED = "cancel:requested"
CANCEL_COMPLETED = "cancel:completed"

# All events for wildcard subscription
ALL_EVENTS = "*"
