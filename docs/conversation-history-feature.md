# Conversation History Feature

## Overview

`simple_chat.py` now maintains **threaded conversation history** so the bot can remember previous questions and provide context-aware responses.

## How It Works

### Before (No History)
```
You: What is CUDA-Q?
Bot: CUDA-Q is...

You: How do I use it?
Bot: [Doesn't know "it" refers to CUDA-Q - treats as new question]
```

### After (With History)
```
You: What is CUDA-Q?
Bot: CUDA-Q is NVIDIA's quantum computing platform...

You: How do I use it?
Bot: [Remembers "it" = CUDA-Q from previous context]
     To use CUDA-Q, you first need to...

You: Can you show me an example?
Bot: [Remembers discussion about CUDA-Q usage]
     Here's an example building on what we discussed...
```

## Implementation

### Message Structure Sent to OpenAI

```python
messages = [
    {"role": "system", "content": "You are a CUDA-Q expert..."},

    # Previous conversation
    {"role": "user", "content": "What is CUDA-Q?"},
    {"role": "assistant", "content": "CUDA-Q is..."},

    {"role": "user", "content": "How do I use it?"},
    {"role": "assistant", "content": "To use CUDA-Q..."},

    # Current question
    {"role": "user", "content": "Can you show me an example?"}
]
```

### History Management

- **Stored**: In memory as list of `{"user": "...", "assistant": "..."}` dicts
- **Limit**: Last 10 exchanges (20 messages) to avoid context overflow
- **Automatic**: Oldest conversations are removed when limit is reached
- **RAG Context**: Retrieved fresh for each query (not stored in history)

### Why 10 Exchanges Limit?

```
Token Budget:
  • RAG context: ~30,000 tokens (aggressive setting)
  • Conversation history: ~2,000 tokens (10 exchanges avg)
  • Current question: ~100 tokens
  • System prompt: ~200 tokens
  • Total: ~32,300 tokens

GPT-4-Turbo limit: 128,000 tokens
Safe with plenty of headroom: ✅
```

## New Commands

### `history` - View Conversation
```bash
You: history

📜 Conversation History (3 turns):
--------------------------------------------------------------------------------

[Turn 1]
You: What is CUDA-Q?...
Bot: CUDA-Q is NVIDIA's platform for hybrid quantum-classical computing. It...

[Turn 2]
You: How do I create a quantum circuit?...
Bot: To create a quantum circuit in CUDA-Q, you use the @cudaq.kernel decora...

[Turn 3]
You: Can you show me an example?...
Bot: Here's an example building on the circuit we discussed: @cudaq.kernel de...
```

### `clear` - Reset Conversation
```bash
You: clear
✅ Conversation history cleared

# Fresh start - bot won't remember previous questions
```

### Display After Each Response
```
🤖 Assistant:
[Response text...]

--------------------------------------------------------------------------------
💬 Conversation turns: 5
--------------------------------------------------------------------------------
```

## Use Cases

### 1. Multi-Step Learning
```
You: What is quantum entanglement?
Bot: Quantum entanglement is...

You: How do I create it in CUDA-Q?
Bot: [Remembers we're discussing entanglement]
     To create entanglement in CUDA-Q...

You: Show me the full code
Bot: [Provides complete example based on discussion]
```

### 2. Iterative Refinement
```
You: Write a quantum Fourier transform
Bot: [Provides code]

You: Can you add error handling?
Bot: [Updates the same code with error handling]

You: Now optimize it for GPU
Bot: [Further refines the same code]
```

### 3. Clarification Questions
```
You: How do I measure qubits?
Bot: There are several ways...

You: Which one is best for my case?
Bot: [Doesn't have "your case" but remembers measurement discussion]
     Based on the measurement methods we discussed, could you clarify...
```

## Context Management

### What's Included in Each Message

```
System Prompt:
  • Role definition
  • RAG context (30,000 tokens from current query)
  • Instructions

Conversation History (up to 10 exchanges):
  • Previous questions
  • Previous answers
  • Limited to avoid overflow

Current Question:
  • User's latest input
```

### What's NOT Included

- **Previous RAG retrievals**: Each query retrieves fresh context
- **Verbose output**: Not sent to LLM
- **System commands**: `history`, `clear`, etc.

## Memory vs Context

### Conversation Memory (What Bot Remembers)
- ✅ Your previous questions
- ✅ Bot's previous answers
- ✅ Topic flow and context
- ❌ OLD documentation chunks (retrieves fresh each time)

### RAG Context (What Bot Searches)
- ✅ Full documentation (always available)
- ✅ Fresh retrieval for each query
- ✅ Ranked by relevance to current question
- ❌ Not stored in conversation history

## Examples

### Example 1: Follow-up Questions
```
You: What's in the latest CUDA-Q release?
Bot: CUDA-Q 0.12.0 was released with...

You: What about the previous version?
Bot: [Remembers we're discussing releases]
     The previous version, 0.11.0, included...

You: How do I upgrade from 0.11 to 0.12?
Bot: [Remembers context of version discussion]
     To upgrade from 0.11.0 to 0.12.0...
```

### Example 2: Code Iteration
```
You: Write a Bell state circuit
Bot: @cudaq.kernel
     def bell_state():
         qubits = cudaq.qvector(2)
         h(qubits[0])
         x.ctrl(qubits[0], qubits[1])

You: Add measurement
Bot: [Updates the same circuit]
     @cudaq.kernel
     def bell_state():
         qubits = cudaq.qvector(2)
         h(qubits[0])
         x.ctrl(qubits[0], qubits[1])
         mz(qubits)

You: How do I run this?
Bot: [Remembers the bell_state circuit we defined]
     To run the bell_state circuit we created...
```

### Example 3: Concept Building
```
You: Explain quantum superposition
Bot: Superposition is...

You: How does that relate to measurement?
Bot: [Remembers superposition discussion]
     When you measure a qubit in superposition...

You: Can you show me this in code?
Bot: [Demonstrates measurement of superposition]
```

## Technical Details

### Storage Location
```python
# In-memory during session
conversation_history = [
    {"user": "question 1", "assistant": "answer 1"},
    {"user": "question 2", "assistant": "answer 2"},
    ...
]
```

### Lifecycle
- **Created**: When chat session starts (empty list)
- **Updated**: After each successful exchange
- **Cleared**: Manual `clear` command or session ends
- **Not Persisted**: Lost when script exits

### Token Counting
```python
# Approximate token counts per exchange
user_message: ~50-200 tokens
assistant_response: ~200-500 tokens
per_exchange: ~250-700 tokens

10_exchanges: ~2,500-7,000 tokens
Still well under limits with 30K RAG context
```

## Best Practices

### When to Clear History
- Starting a completely new topic
- Conversation becomes confused
- Hit the 10-exchange limit and need fresh context

### When NOT to Clear
- Follow-up questions on same topic
- Iterating on code examples
- Multi-step learning process

## Troubleshooting

### "Bot doesn't remember my question"
- Check: `history` command to see what's stored
- Solution: Make sure you're in the same session

### "Bot responses get confused"
- Cause: Too many topic switches in history
- Solution: Use `clear` to reset

### "Context too long error"
- Cause: Rare, but 10 exchanges + 30K RAG might overflow
- Solution: `clear` history or reduce `max_tokens` in RAG

## Configuration

### Adjust History Limit
```python
# In simple_chat.py line 239
if len(conversation_history) > 10:  # Change this number
    conversation_history = conversation_history[-10:]
```

### Disable History (Stateless Mode)
```python
# Comment out lines 233-240
# conversation_history.append({...})
# if len(conversation_history) > 10:
#     ...
```

## Summary

**Feature**: Full conversation history with context awareness

**Storage**: In-memory, last 10 exchanges

**Benefits**:
- Follow-up questions work naturally
- Code iteration is seamless
- Multi-turn conversations flow better

**Commands**:
- `history` - View conversation
- `clear` - Reset conversation
- Automatic display of turn count after each response
