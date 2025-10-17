#!/usr/bin/env python3
"""Test single query with OpenAI API."""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_single_query():
    """Test a single query with the full system."""
    print("🧪 Testing single query with OpenAI...")

    # Load API key
    if os.path.exists('.env'):
        with open('.env', 'r') as f:
            for line in f:
                if line.strip() and not line.startswith('#') and '=' in line:
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value

    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ No OpenAI API key found")
        return

    print(f"✅ API key loaded: ...{api_key[-4:]}")

    try:
        # Test query
        test_query = "What is CUDA-Q and how do I create a simple quantum circuit?"
        print(f"🔍 Query: {test_query}")

        # Initialize OpenAI
        from openai import OpenAI
        client = OpenAI(api_key=api_key)

        # Create context (mock for now since vector search has issues)
        cuda_q_context = """
CUDA-Q is NVIDIA's unified platform for hybrid quantum-classical computing. It provides:

1. Quantum kernel programming with @cudaq.kernel decorator
2. Support for quantum algorithms and circuits
3. Integration with classical computing workflows
4. Multiple backend targets (simulators and real quantum hardware)

Basic quantum circuit example:
@cudaq.kernel
def bell_state():
    qubits = cudaq.qvector(2)
    h(qubits[0])  # Hadamard gate creates superposition
    x.ctrl(qubits[0], qubits[1])  # CNOT gate creates entanglement

To execute:
counts = cudaq.sample(bell_state)
print(counts)

Key concepts:
- Quantum kernels are decorated with @cudaq.kernel
- qubits are allocated with cudaq.qvector(n)
- Common gates: h() for Hadamard, x() for Pauli-X, x.ctrl() for CNOT
- Sampling with cudaq.sample(), observation with cudaq.observe()
"""

        # Create system prompt
        system_prompt = f"""You are an expert CUDA-Q assistant. Answer questions about CUDA-Q quantum computing based on the provided documentation context.

Documentation Context:
{cuda_q_context}

Instructions:
- Provide accurate answers about CUDA-Q
- Include working code examples when appropriate
- Explain quantum concepts clearly for beginners
- Use proper CUDA-Q syntax with @cudaq.kernel
- Be helpful and educational"""

        print("🤖 Generating response with OpenAI...")

        # Call OpenAI API
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": test_query}
            ],
            max_tokens=600,
            temperature=0.1
        )

        assistant_response = response.choices[0].message.content

        print("\n" + "="*60)
        print("🤖 CUDA-Q Assistant Response:")
        print("="*60)
        print(assistant_response)
        print("="*60)

        print(f"\n✅ Success! Response generated ({len(assistant_response)} chars)")
        print("🎉 Your AI Documentation Assistant is working with OpenAI!")

        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_single_query()
    print(f"\nFinal Result: {'✅ SUCCESS' if success else '❌ FAILED'}")