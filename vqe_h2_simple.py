"""
Simple VQE Example for H2 Molecule using CUDA Quantum

Purpose:
--------
This is a simplified VQE (Variational Quantum Eigensolver) example using the
hydrogen molecule (H2). This serves as a gentler introduction to VQE before
tackling more complex molecules like H2O.

The H2 molecule requires only 4 qubits, making it easier to understand and
faster to compute than larger molecules.

Example Use:
-----------
python vqe_h2_simple.py

The script will output:
1. Molecular configuration
2. VQE optimization progress
3. Ground state energy comparison with exact results

Requirements:
------------
- CUDA Quantum (cudaq)
- NumPy
- SciPy

Installation:
------------
pip install cudaq scipy numpy

Note:
-----
This example uses a pre-computed Hamiltonian for H2 at equilibrium bond length.
For automatic Hamiltonian generation from molecular geometry, see vqe_h2o_example.py

Author: CUDA Quantum Example
"""

import cudaq
from cudaq import spin
import numpy as np
from scipy.optimize import minimize
from typing import List


def get_h2_hamiltonian():
    """
    Returns the Hamiltonian for H2 molecule at equilibrium geometry.
    
    This uses the pre-computed Hamiltonian for H2 at bond length 0.7414 Å
    in the STO-3G basis set, mapped to qubits using Jordan-Wigner transformation.
    
    Returns:
    -------
    tuple: (hamiltonian, num_qubits, fci_energy)
    """
    # H2 Hamiltonian coefficients (in Hartree)
    # These are the Pauli string coefficients for H2 at equilibrium
    
    # Create the Hamiltonian using CUDA Quantum spin operators
    hamiltonian = -1.0523732 * spin.i(0)  # Identity term
    hamiltonian += 0.39793742 * spin.z(0)
    hamiltonian += -0.39793742 * spin.z(1)
    hamiltonian += -0.01128010 * spin.z(2)
    hamiltonian += 0.01128010 * spin.z(3)
    hamiltonian += 0.18093119 * spin.z(0) * spin.z(1)
    hamiltonian += 0.16614543 * spin.z(0) * spin.z(2)
    hamiltonian += 0.16614543 * spin.z(0) * spin.z(3)
    hamiltonian += 0.12091263 * spin.z(1) * spin.z(2)
    hamiltonian += 0.12091263 * spin.z(1) * spin.z(3)
    hamiltonian += 0.17464343 * spin.z(2) * spin.z(3)
    
    # Add X and Y terms
    hamiltonian += 0.04523279 * spin.x(0) * spin.x(1) * spin.y(2) * spin.y(3)
    hamiltonian += 0.04523279 * spin.y(0) * spin.y(1) * spin.x(2) * spin.x(3)
    hamiltonian += 0.04523279 * spin.x(0) * spin.y(1) * spin.y(2) * spin.x(3)
    hamiltonian += -0.04523279 * spin.y(0) * spin.x(1) * spin.x(2) * spin.y(3)
    
    num_qubits = 4
    fci_energy = -1.137283834488  # Exact ground state energy
    
    return hamiltonian, num_qubits, fci_energy


@cudaq.kernel
def ansatz(qubits: cudaq.qview, params: List[float]):
    """
    Simple parameterized quantum circuit (ansatz) for H2.
    
    This uses a hardware-efficient ansatz with:
    - Hartree-Fock initialization (2 electrons in 4 spin orbitals)
    - Parameterized rotation gates
    - Entangling CNOT gates
    
    Parameters:
    ----------
    qubits: cudaq.qview
        Quantum register (4 qubits for H2)
    params: List[float]
        Variational parameters
    """
    # Initialize to Hartree-Fock state for H2 (2 electrons)
    # First 2 spin orbitals occupied: |1100⟩
    x(qubits[0])
    x(qubits[1])
    
    # Parameterized circuit layers
    num_qubits = qubits.size()
    param_idx = 0
    
    # Layer 1: Single-qubit rotations
    for i in range(num_qubits):
        if param_idx < len(params):
            ry(params[param_idx], qubits[i])
            param_idx += 1
    
    # Entangling layer
    cx(qubits[0], qubits[1])
    cx(qubits[1], qubits[2])
    cx(qubits[2], qubits[3])
    
    # Layer 2: More rotations
    for i in range(num_qubits):
        if param_idx < len(params):
            rz(params[param_idx], qubits[i])
            param_idx += 1
    
    # Second entangling layer
    cx(qubits[3], qubits[2])
    cx(qubits[2], qubits[1])
    cx(qubits[1], qubits[0])
    
    # Layer 3: Final rotations
    for i in range(num_qubits):
        if param_idx < len(params):
            ry(params[param_idx], qubits[i])
            param_idx += 1


def main():
    """
    Main function to run VQE for H2 molecule.
    """
    print("=" * 80)
    print("SIMPLE VQE EXAMPLE: H2 MOLECULE")
    print("=" * 80)
    
    # Set target backend
    cudaq.set_target('qpp-cpu')
    
    # Get H2 Hamiltonian
    hamiltonian, num_qubits, exact_energy = get_h2_hamiltonian()
    
    print(f"\nMolecule: H2 (Hydrogen)")
    print(f"Bond length: 0.7414 Å")
    print(f"Basis set: STO-3G")
    print(f"Number of qubits: {num_qubits}")
    print(f"Exact ground state energy: {exact_energy:.8f} Ha")
    
    # VQE parameters
    num_parameters = 12  # 3 layers × 4 qubits
    print(f"\nVQE Configuration:")
    print(f"  Ansatz: Hardware-efficient")
    print(f"  Parameters: {num_parameters}")
    print(f"  Optimizer: COBYLA")
    
    # Initialize parameters
    np.random.seed(42)
    initial_params = np.random.randn(num_parameters) * 0.1
    
    # Track optimization
    iteration = [0]
    energies = []
    
    def objective(params):
        """Compute energy expectation value."""
        energy = cudaq.observe(ansatz, hamiltonian, num_qubits, params.tolist()).expectation()
        return energy
    
    def callback(xk):
        """Track optimization progress."""
        iteration[0] += 1
        energy = objective(xk)
        energies.append(energy)
        if iteration[0] % 5 == 0 or iteration[0] == 1:
            error = abs(energy - exact_energy)
            print(f"  Iter {iteration[0]:3d}: Energy = {energy:.8f} Ha  |  Error = {error:.8f} Ha")
    
    print("\n" + "=" * 80)
    print("Starting VQE Optimization")
    print("=" * 80)
    
    initial_energy = objective(initial_params)
    print(f"Initial energy: {initial_energy:.8f} Ha\n")
    
    # Run optimization
    result = minimize(
        objective,
        initial_params,
        method='COBYLA',
        callback=callback,
        options={'maxiter': 100, 'rhobeg': 0.5}
    )
    
    # Final results
    vqe_energy = result.fun
    error = abs(vqe_energy - exact_energy)
    error_kcal = error * 627.509  # Convert to kcal/mol
    
    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)
    print(f"\n{'Exact (FCI) Energy:':<30} {exact_energy:.8f} Ha")
    print(f"{'VQE Energy:':<30} {vqe_energy:.8f} Ha")
    print(f"\n{'Absolute Error:':<30} {error:.8f} Ha")
    print(f"{'Absolute Error:':<30} {error_kcal:.4f} kcal/mol")
    print(f"{'Relative Error:':<30} {(error/abs(exact_energy)*100):.4f} %")
    
    # Check chemical accuracy
    if error_kcal < 1.6:
        print(f"\n✓ Chemical accuracy achieved! (< 1.6 kcal/mol)")
    else:
        print(f"\n⚠ Not within chemical accuracy (goal: < 1.6 kcal/mol)")
    
    print(f"\nTotal iterations: {iteration[0]}")
    print(f"Optimization success: {result.success}")
    
    # Show energy convergence
    if len(energies) > 0:
        print("\n" + "=" * 80)
        print("Energy Convergence Summary")
        print("=" * 80)
        print(f"  Initial energy:  {energies[0]:.8f} Ha")
        print(f"  Final energy:    {energies[-1]:.8f} Ha")
        print(f"  Energy lowered:  {(energies[0] - energies[-1]):.8f} Ha")
        print(f"  Energy lowered:  {(energies[0] - energies[-1]) * 627.509:.4f} kcal/mol")
    
    print("\n" + "=" * 80)
    print("Next Steps:")
    print("=" * 80)
    print("- Try vqe_h2o_example.py for a more complex molecule")
    print("- Experiment with different ansatz structures")
    print("- Try different optimizers (L-BFGS-B, Powell, etc.)")
    print("- Use GPU: cudaq.set_target('nvidia')")
    print("=" * 80)
    print()


if __name__ == "__main__":
    main()


