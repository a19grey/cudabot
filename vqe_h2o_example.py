"""
VQE (Variational Quantum Eigensolver) for H2O Molecule using CUDA Quantum

Purpose:
--------
This script demonstrates the use of the Variational Quantum Eigensolver (VQE) algorithm
to compute the ground state energy of a water (H2O) molecule using CUDA Quantum.

VQE is a hybrid quantum-classical algorithm that:
1. Prepares a parameterized quantum state (ansatz) on a quantum computer
2. Measures the expectation value of the molecular Hamiltonian
3. Uses classical optimization to update parameters and minimize the energy

The water molecule is set up with:
- Molecular geometry: O at origin, H atoms at specific positions
- Basis set: sto-3g (minimal basis)
- Active space reduction to make computation tractable
- UCCSD (Unitary Coupled Cluster Singles and Doubles) ansatz

Example Use:
-----------
python vqe_h2o_example.py

The script will output:
1. Molecular geometry and configuration
2. Number of qubits and parameters
3. VQE optimization progress
4. Final ground state energy and comparison with classical results

Requirements:
------------
- CUDA Quantum (cudaq)
- OpenFermion
- OpenFermion-PySCF
- SciPy (for optimization)
- NumPy

Installation:
------------
pip install cudaq openfermion openfermionpyscf scipy numpy

Note:
-----
For larger molecules, consider using GPU acceleration with cudaq.set_target('nvidia')
or cudaq.set_target('nvidia-mgpu') for multi-GPU systems.

Author: CUDA Quantum Example
"""

import cudaq
from cudaq import spin
import numpy as np
from typing import List
from scipy.optimize import minimize

# Import required chemistry libraries
try:
    import openfermion
    from openfermion import MolecularData
    from openfermionpyscf import run_pyscf
except ImportError as e:
    print("Error: Required chemistry libraries not found.")
    print("Please install: pip install openfermion openfermionpyscf")
    raise e


def get_h2o_hamiltonian():
    """
    Generate the molecular Hamiltonian for the H2O molecule.
    
    This function:
    1. Defines the molecular geometry
    2. Runs classical electronic structure calculations
    3. Converts the Hamiltonian to qubit operators using Jordan-Wigner transform
    
    Returns:
    -------
    tuple: (cudaq_hamiltonian, num_qubits, nuclear_repulsion, fci_energy, molecule_info)
        - cudaq_hamiltonian: The Hamiltonian as a cudaq.SpinOperator
        - num_qubits: Number of qubits required
        - nuclear_repulsion: Nuclear repulsion energy
        - fci_energy: Full Configuration Interaction (exact) energy for comparison
        - molecule_info: Dictionary with molecular details
    """
    print("=" * 80)
    print("Setting up H2O Molecule Hamiltonian")
    print("=" * 80)
    
    # Define the geometry of water molecule
    # Coordinates in Angstroms: O at origin, H atoms positioned
    geometry = [
        ['O', [0.0000, 0.0000, 0.0000]],
        ['H', [0.0000, 0.7569, 0.5869]],
        ['H', [0.0000, -0.7569, 0.5869]]
    ]
    
    # Molecular parameters
    basis = 'sto-3g'  # Minimal basis set
    multiplicity = 1  # Singlet state
    charge = 0        # Neutral molecule
    
    print(f"\nMolecular Geometry:")
    for atom, coord in geometry:
        print(f"  {atom}: ({coord[0]:7.4f}, {coord[1]:7.4f}, {coord[2]:7.4f}) Angstroms")
    
    print(f"\nBasis Set: {basis}")
    print(f"Charge: {charge}")
    print(f"Multiplicity: {multiplicity}")
    
    # Create MolecularData object
    molecule = MolecularData(
        geometry,
        basis,
        multiplicity,
        charge,
        description="H2O"
    )
    
    print("\nRunning classical electronic structure calculation (PySCF)...")
    # Run PySCF to get molecular integrals and FCI energy
    molecule = run_pyscf(
        molecule,
        run_scf=True,
        run_fci=True
    )
    
    # Get the Hamiltonian in fermionic representation
    hamiltonian = molecule.get_molecular_hamiltonian()
    
    # Convert to fermion operator
    fermion_hamiltonian = openfermion.get_fermion_operator(hamiltonian)
    
    # Apply Jordan-Wigner transformation to convert to qubit operators
    qubit_hamiltonian = openfermion.jordan_wigner(fermion_hamiltonian)
    
    # Get number of qubits (2 * number of spatial orbitals)
    num_qubits = molecule.n_qubits
    
    print(f"\nNumber of qubits required: {num_qubits}")
    print(f"Number of electrons: {molecule.n_electrons}")
    print(f"Number of orbitals: {molecule.n_orbitals}")
    
    # Convert OpenFermion QubitOperator to CUDA Quantum SpinOperator
    cudaq_hamiltonian = convert_to_cudaq_hamiltonian(qubit_hamiltonian, num_qubits)
    
    # Get classical reference energies
    nuclear_repulsion = molecule.nuclear_repulsion
    fci_energy = molecule.fci_energy
    hf_energy = molecule.hf_energy
    
    print(f"\nClassical Reference Energies:")
    print(f"  Nuclear Repulsion: {nuclear_repulsion:.8f} Ha")
    print(f"  Hartree-Fock:     {hf_energy:.8f} Ha")
    print(f"  FCI (Exact):      {fci_energy:.8f} Ha")
    
    molecule_info = {
        'name': 'H2O',
        'geometry': geometry,
        'basis': basis,
        'n_qubits': num_qubits,
        'n_electrons': molecule.n_electrons,
        'n_orbitals': molecule.n_orbitals
    }
    
    return cudaq_hamiltonian, num_qubits, nuclear_repulsion, fci_energy, molecule_info


def convert_to_cudaq_hamiltonian(openfermion_op, num_qubits):
    """
    Convert an OpenFermion QubitOperator to a CUDA Quantum SpinOperator.
    
    Parameters:
    ----------
    openfermion_op: OpenFermion QubitOperator
        The Hamiltonian in OpenFermion format
    num_qubits: int
        Number of qubits in the system
    
    Returns:
    -------
    cudaq.SpinOperator: The Hamiltonian in CUDA Quantum format
    """
    # Start with zero operator
    hamiltonian = 0.0
    
    # Iterate through all terms in the OpenFermion operator
    for term, coeff in openfermion_op.terms.items():
        if len(term) == 0:
            # Identity term (constant)
            hamiltonian += float(coeff.real)
        else:
            # Build the Pauli string
            pauli_word = 1.0
            for qubit_idx, pauli_op in term:
                if pauli_op == 'X':
                    pauli_word *= spin.x(qubit_idx)
                elif pauli_op == 'Y':
                    pauli_word *= spin.y(qubit_idx)
                elif pauli_op == 'Z':
                    pauli_word *= spin.z(qubit_idx)
            hamiltonian += float(coeff.real) * pauli_word
    
    return hamiltonian


@cudaq.kernel
def uccsd_ansatz(qubits: cudaq.qview, thetas: List[float]):
    """
    UCCSD (Unitary Coupled Cluster Singles and Doubles) ansatz.
    
    This is a simplified UCCSD-inspired ansatz that prepares the quantum state.
    For a full UCCSD implementation, use the chemistry module with actual
    excitation operators generated from the molecular structure.
    
    Parameters:
    ----------
    qubits: cudaq.qview
        Quantum register
    thetas: List[float]
        Variational parameters
    """
    # Prepare Hartree-Fock reference state (for H2O with 10 electrons)
    # In sto-3g basis, H2O has 7 spatial orbitals = 14 spin orbitals
    # 10 electrons means first 10 spin orbitals are occupied
    # This corresponds to qubits 0-9 being in |1⟩ state
    
    num_qubits = qubits.size()
    num_electrons = min(10, num_qubits)  # H2O has 10 electrons
    
    # Prepare Hartree-Fock state: flip first num_electrons qubits to |1⟩
    for i in range(num_electrons):
        x(qubits[i])
    
    # Apply parameterized gates - hardware-efficient ansatz
    # This is a simplified version; full UCCSD would have specific excitation operators
    
    # Calculate number of parameters needed
    # We'll use a layered approach with entangling gates
    param_idx = 0
    num_layers = len(thetas) // (num_qubits * 2) if len(thetas) >= num_qubits * 2 else 1
    
    for layer in range(num_layers):
        # Single-qubit rotations
        for i in range(num_qubits):
            if param_idx < len(thetas):
                ry(thetas[param_idx], qubits[i])
                param_idx += 1
        
        # Entangling layer
        for i in range(num_qubits):
            if param_idx < len(thetas):
                rz(thetas[param_idx], qubits[i])
                param_idx += 1
        
        # CNOT ladder for entanglement
        for i in range(num_qubits - 1):
            cx(qubits[i], qubits[i + 1])


def vqe_objective(parameters, hamiltonian, num_qubits):
    """
    VQE objective function to minimize.
    
    This function prepares the quantum state with given parameters
    and computes the expectation value of the Hamiltonian.
    
    Parameters:
    ----------
    parameters: np.ndarray
        Variational parameters
    hamiltonian: cudaq.SpinOperator
        Molecular Hamiltonian
    num_qubits: int
        Number of qubits
    
    Returns:
    -------
    float: Energy expectation value
    """
    # Compute expectation value using CUDA Quantum
    energy = cudaq.observe(uccsd_ansatz, hamiltonian, num_qubits, parameters.tolist()).expectation()
    
    return energy


def run_vqe_optimization(hamiltonian, num_qubits, num_parameters):
    """
    Run the VQE optimization loop.
    
    Parameters:
    ----------
    hamiltonian: cudaq.SpinOperator
        Molecular Hamiltonian
    num_qubits: int
        Number of qubits
    num_parameters: int
        Number of variational parameters
    
    Returns:
    -------
    tuple: (optimal_energy, optimal_parameters, optimization_result)
    """
    print("\n" + "=" * 80)
    print("Starting VQE Optimization")
    print("=" * 80)
    print(f"\nNumber of parameters: {num_parameters}")
    
    # Initialize parameters (small random values near zero)
    np.random.seed(42)  # For reproducibility
    initial_parameters = np.random.randn(num_parameters) * 0.01
    
    print(f"Optimization method: COBYLA (Constrained Optimization BY Linear Approximation)")
    print(f"Initial energy evaluation...")
    
    # Evaluation counter for progress tracking
    iteration_count = [0]
    energies = []
    
    def callback(xk):
        """Callback function to track optimization progress."""
        iteration_count[0] += 1
        energy = vqe_objective(xk, hamiltonian, num_qubits)
        energies.append(energy)
        if iteration_count[0] % 10 == 0:
            print(f"  Iteration {iteration_count[0]:4d}: Energy = {energy:.8f} Ha")
    
    initial_energy = vqe_objective(initial_parameters, hamiltonian, num_qubits)
    print(f"  Initial energy: {initial_energy:.8f} Ha")
    print(f"\nOptimizing...")
    
    # Run optimization
    result = minimize(
        fun=lambda x: vqe_objective(x, hamiltonian, num_qubits),
        x0=initial_parameters,
        method='COBYLA',
        callback=callback,
        options={'maxiter': 200, 'rhobeg': 0.5, 'tol': 1e-6}
    )
    
    optimal_energy = result.fun
    optimal_parameters = result.x
    
    print(f"\nOptimization completed!")
    print(f"  Final energy: {optimal_energy:.8f} Ha")
    print(f"  Total iterations: {iteration_count[0]}")
    print(f"  Success: {result.success}")
    
    return optimal_energy, optimal_parameters, result


def main():
    """
    Main function to run the VQE calculation for H2O.
    """
    print("\n" + "=" * 80)
    print("VQE FOR H2O MOLECULE - CUDA QUANTUM")
    print("=" * 80)
    
    # Set CUDA Quantum target
    # Options: 'qpp-cpu', 'nvidia', 'nvidia-mgpu'
    target = 'qpp-cpu'
    cudaq.set_target(target)
    print(f"\nCUDA Quantum Target: {target}")
    
    # Step 1: Generate the H2O Hamiltonian
    hamiltonian, num_qubits, nuclear_repulsion, fci_energy, molecule_info = get_h2o_hamiltonian()
    
    # Step 2: Set up the VQE ansatz
    # For this example, we'll use a hardware-efficient ansatz
    # with 2 layers of parameterized gates
    num_layers = 2
    num_parameters = num_layers * num_qubits * 2
    
    print("\n" + "=" * 80)
    print("VQE Configuration")
    print("=" * 80)
    print(f"Ansatz: Hardware-efficient (layered)")
    print(f"Number of layers: {num_layers}")
    print(f"Number of parameters: {num_parameters}")
    
    # Step 3: Run VQE optimization
    vqe_energy, optimal_params, opt_result = run_vqe_optimization(
        hamiltonian,
        num_qubits,
        num_parameters
    )
    
    # Step 4: Display results and comparison
    print("\n" + "=" * 80)
    print("FINAL RESULTS")
    print("=" * 80)
    
    print(f"\nMolecule: {molecule_info['name']}")
    print(f"Basis Set: {molecule_info['basis']}")
    print(f"Number of Qubits: {molecule_info['n_qubits']}")
    
    print(f"\n{'Energy Comparison:':<30}")
    print(f"  {'FCI (Exact):':<25} {fci_energy:.8f} Ha")
    print(f"  {'VQE:':<25} {vqe_energy:.8f} Ha")
    
    error = abs(vqe_energy - fci_energy)
    error_kcal = error * 627.509  # Convert Hartree to kcal/mol
    
    print(f"\n{'Error Analysis:':<30}")
    print(f"  {'Absolute Error:':<25} {error:.8f} Ha")
    print(f"  {'Absolute Error:':<25} {error_kcal:.4f} kcal/mol")
    print(f"  {'Relative Error:':<25} {(error/abs(fci_energy)*100):.4f} %")
    
    # Chemical accuracy is typically 1.6 kcal/mol
    chemical_accuracy = 1.6 / 627.509  # in Hartree
    if error < chemical_accuracy:
        print(f"\n✓ Result is within chemical accuracy (1.6 kcal/mol)!")
    else:
        print(f"\n⚠ Result is NOT within chemical accuracy.")
        print(f"  Consider increasing number of layers or using better ansatz.")
    
    print("\n" + "=" * 80)
    print("Optimization Statistics")
    print("=" * 80)
    print(f"  Optimization method: {opt_result.get('message', 'N/A')}")
    print(f"  Number of iterations: {opt_result.get('nfev', 'N/A')}")
    print(f"  Success: {opt_result.success}")
    
    print("\n" + "=" * 80)
    print("Notes:")
    print("=" * 80)
    print("- This example uses a simplified hardware-efficient ansatz")
    print("- For better accuracy, consider:")
    print("  1. Using full UCCSD ansatz with proper excitation operators")
    print("  2. Increasing the number of layers")
    print("  3. Using better optimization methods (e.g., L-BFGS-B)")
    print("  4. Active space reduction for larger molecules")
    print("- For GPU acceleration, use: cudaq.set_target('nvidia')")
    print("=" * 80)
    print()


if __name__ == "__main__":
    main()


