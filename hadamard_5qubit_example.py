"""
5-Qubit Hadamard Gate Example using CUDA Quantum

Purpose:
--------
This script demonstrates the application of Hadamard gates to a 5-qubit quantum system
using CUDA Quantum. The Hadamard gate creates a superposition state by transforming
|0⟩ → (|0⟩ + |1⟩)/√2 and |1⟩ → (|0⟩ - |1⟩)/√2.

When applied to all 5 qubits initialized to |0⟩, the result is an equal superposition
of all 2^5 = 32 possible basis states, each with amplitude 1/√32 ≈ 0.1768.

Example Use:
-----------
python hadamard_5qubit_example.py

The script will output:
1. A circuit diagram showing the Hadamard gates
2. The complete statevector with all 32 amplitudes
3. A summary of the quantum state properties

Requirements:
------------
- CUDA Quantum (cudaq)
- NumPy

Author: CUDA Quantum Example
"""

import cudaq
import numpy as np


# Define the quantum kernel that applies Hadamard gates to 5 qubits
@cudaq.kernel
def hadamard_5qubits():
    """
    Quantum kernel that creates a 5-qubit register and applies
    Hadamard gates to each qubit, creating a uniform superposition.
    """
    # Create a quantum register with 5 qubits (all initialized to |0⟩)
    qubits = cudaq.qvector(5)
    
    # Apply Hadamard gate to each qubit
    h(qubits[0])
    h(qubits[1])
    h(qubits[2])
    h(qubits[3])
    h(qubits[4])


def main():
    """
    Main function to execute the quantum circuit and display results.
    """
    # Set the target backend (qpp-cpu for CPU simulation)
    cudaq.set_target('qpp-cpu')
    
    print("=" * 80)
    print("5-Qubit Hadamard Gate Example - CUDA Quantum")
    print("=" * 80)
    print()
    
    # Display the circuit diagram
    print("Circuit Diagram:")
    print("-" * 80)
    print(cudaq.draw(hadamard_5qubits))
    print()
    
    # Get the statevector after applying Hadamard gates
    print("Executing quantum circuit...")
    statevector = cudaq.get_state(hadamard_5qubits)
    
    print()
    print("=" * 80)
    print("Quantum State After Applying Hadamard Gates")
    print("=" * 80)
    print()
    
    # Convert to numpy array for easier manipulation
    state_array = np.array(statevector)
    
    # Display the full statevector
    print("Complete Statevector (32 basis states):")
    print("-" * 80)
    for i, amplitude in enumerate(state_array):
        # Convert index to binary representation
        binary_state = format(i, '05b')
        # Display each basis state with its amplitude
        print(f"|{binary_state}⟩: {amplitude.real:+.6f} {amplitude.imag:+.6f}j  "
              f"(magnitude: {abs(amplitude):.6f})")
    
    print()
    print("=" * 80)
    print("State Properties")
    print("=" * 80)
    print(f"Total number of basis states: {len(state_array)}")
    print(f"Expected amplitude (1/√32): {1/np.sqrt(32):.6f}")
    print(f"Actual amplitude magnitude: {abs(state_array[0]):.6f}")
    print(f"Sum of probability amplitudes: {np.sum(np.abs(state_array)**2):.6f}")
    print()
    
    # Verify uniform superposition
    magnitudes = np.abs(state_array)
    is_uniform = np.allclose(magnitudes, magnitudes[0])
    print(f"Uniform superposition verified: {is_uniform}")
    print()
    
    # Additional analysis
    print("=" * 80)
    print("Probability Distribution")
    print("=" * 80)
    probabilities = np.abs(state_array)**2
    print(f"Each basis state has probability: {probabilities[0]:.6f} ({probabilities[0]*100:.2f}%)")
    print(f"Expected probability (1/32): {1/32:.6f} ({100/32:.2f}%)")
    print()
    
    print("This uniform superposition means that if measured, each of the 32 possible")
    print("5-qubit computational basis states has an equal 3.125% chance of being observed.")
    print()


if __name__ == "__main__":
    main()

