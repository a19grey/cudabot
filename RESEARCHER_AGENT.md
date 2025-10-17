# Intelligent Researcher Agent

## Problem Solved

The basic RAG search was "dumb" - it would just embed the user's query and search for similar embeddings. This often failed because:

1. **Query-Document Mismatch**: User queries use different language than documentation
2. **Poor Query Formulation**: Users don't always phrase questions optimally for search
3. **No Evaluation**: No way to know if results are actually relevant
4. **No Iteration**: Can't refine searches when initial results are poor

## Solution: Researcher Agent

The new researcher agent acts as an intelligent intermediary between the user and the RAG system:

```
User Query → Researcher Agent → Smart RAG Search → Evaluated Results → Main Conversation Agent
```

### What the Researcher Agent Does

#### 1. **Query Analysis**
- Understands the user's intent (how-to, what-is, example, troubleshooting, etc.)
- Extracts key concepts and technical terms
- Determines what type of documentation would best answer the query

#### 2. **Strategic Query Reformulation**
- Converts user language into documentation language
- Uses domain-specific terminology (e.g., "VQE" instead of "variational quantum eigensolver algorithm")
- Considers multiple search angles
- Thinks about how documentation is typically structured

#### 3. **Intelligent Search**
- Uses the `smart_search_tool` to query the vector database
- Requests more candidates initially (lower threshold of 0.4)
- Gets back structured results with similarity scores

#### 4. **Result Evaluation**
- Uses the `evaluate_results_tool` to assess quality
- Checks similarity scores and relevance
- Determines confidence level
- Identifies if results adequately answer the query

#### 5. **Iterative Refinement**
- If initial results are poor (confidence < 0.6), tries alternative approaches:
  - Different terminology or phrasing
  - Breaking complex queries into sub-queries
  - Searching for related concepts
  - Broadening or narrowing scope
- Can iterate up to 15 times to find good results

#### 6. **Selection and Reporting**
- Selects only high-quality chunks (similarity > 0.5)
- Prioritizes 3-5 excellent chunks over many mediocre ones
- Returns structured report with:
  - Search strategy used
  - Selected documentation chunks with scores
  - Confidence assessment
  - Recommendations for follow-up

## Architecture

### File Structure
```
src/agents/researcher_agent.py         # Main researcher agent implementation
src/orchestration/crew_flow.py         # Integration into conversation flow
config/targets/cuda_q.yaml             # Researcher agent configuration
```

### Key Components

#### Tools
1. **`smart_search_tool`** - Performs RAG search with lower threshold, returns structured results
2. **`evaluate_results_tool`** - Assesses result quality and confidence

#### Agent Configuration
```yaml
researcher_agent:
  role: "CUDA-Q Research Specialist"
  goal: "Intelligently search and find the most relevant CUDA-Q documentation through strategic query reformulation"
  max_iter: 15  # Allow multiple iterations for refinement
```

#### Workflow Integration
```python
# Old Flow
User Query → Query Agent → RAG Search → Results

# New Flow
User Query → Researcher Agent → [Analyze → Reformulate → Search → Evaluate → Iterate] → Best Results → Main Agent
```

## Example Workflow

### User asks: "How do I optimize my quantum circuit?"

1. **Analysis**:
   - Intent: how-to
   - Type: optimization/performance
   - Key concepts: circuit, optimization

2. **Reformulation attempts**:
   - Try 1: "quantum circuit optimization"
   - Try 2: "circuit optimization techniques CUDA-Q"
   - Try 3: "optimize kernel cudaq circuit"

3. **Search & Evaluate**:
   - Search 1: avg_similarity=0.45, confidence=0.5 → needs improvement
   - Search 2: avg_similarity=0.62, confidence=0.7 → good enough!

4. **Select Best**:
   - Chunk 1: "Circuit Optimization Guide" (similarity: 0.72)
   - Chunk 2: "Performance Best Practices" (similarity: 0.68)
   - Chunk 3: "Kernel Optimization Examples" (similarity: 0.65)

5. **Report**:
   - Strategy: Used CUDA-Q specific terminology
   - Confidence: 0.7/1.0
   - Recommendation: Results should answer the query well

## Configuration

### Similarity Thresholds
- **Researcher search**: 0.4 (permissive, let agent evaluate)
- **Final selection**: 0.5 (only pass on relevant results)
- **High confidence**: 0.6+ average similarity

### Search Parameters
```python
# Researcher Agent
max_chunks: 10           # Get more candidates
similarity_threshold: 0.4  # Lower threshold for evaluation
max_iter: 15            # Allow multiple refinement attempts

# Final Selection
similarity_threshold: 0.5  # Only return relevant results
top_k: 3-5              # Quality over quantity
```

## Usage

### Running the system
```bash
# Normal chat (uses researcher agent automatically)
python src/main.py chat --target cuda_q --query "How do I use VQE?"

# Test the researcher agent specifically
python test_researcher.py
```

### Direct integration
```python
from agents.researcher_agent import create_researcher_agent, create_research_task
from crewai import Crew, Process

# Create researcher
researcher = create_researcher_agent(collection, config)
task = create_research_task("How do I use VQE?", researcher, config)

# Execute research
crew = Crew(agents=[researcher], tasks=[task], process=Process.sequential)
result = crew.kickoff()
```

## Benefits

1. **Better Results**: Finds more relevant documentation through smart reformulation
2. **Higher Confidence**: Evaluates and iterates until results are good
3. **Transparency**: Shows what searches were tried and why
4. **Adaptability**: Can adjust strategy based on results
5. **Quality Filter**: Only passes high-quality chunks to main agent

## Future Enhancements

1. **Learning**: Track which reformulations work best and learn patterns
2. **Multi-hop**: Search for related concepts and combine information
3. **Semantic clustering**: Group similar results to avoid redundancy
4. **Citation tracking**: Keep track of source documents for better attribution
5. **Query expansion**: Use retrieved docs to expand query with related terms
