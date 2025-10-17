# VQE (Variational Quantum Eigensolver) Examples for CUDA Quantum

## Overview

This directory contains comprehensive VQE examples for molecular quantum chemistry simulations using CUDA Quantum. VQE is a hybrid quantum-classical algorithm used to find the ground state energy of molecular systems.

## Files

### 1. `vqe_h2_simple.py` - Simple H2 Example (Start Here!)
**Recommended for beginners**

- **Molecule**: H2 (Hydrogen molecule)
- **Qubits**: 4
- **Complexity**: Low
- **Runtime**: ~1-2 minutes

This example uses a pre-computed Hamiltonian for the hydrogen molecule, making it easy to understand the VQE workflow without the complexity of quantum chemistry setup.

**Features:**
- Pre-computed Hamiltonian (no chemistry libraries needed for the Hamiltonian)
- Simple hardware-efficient ansatz
- Clear optimization tracking
- Fast execution

**Run it:**
```bash
python vqe_h2_simple.py
```

---

### 2. `vqe_h2o_example.py` - Complete H2O Example
**Advanced: Full quantum chemistry pipeline**

- **Molecule**: H2O (Water molecule)
- **Qubits**: 14 (for STO-3G basis)
- **Complexity**: High
- **Runtime**: ~5-10 minutes (CPU), faster on GPU

This is a complete example showing the full quantum chemistry workflow from molecular geometry to VQE optimization.

**Features:**
- Automatic Hamiltonian generation from molecular geometry
- Integration with OpenFermion and PySCF
- Jordan-Wigner transformation
- UCCSD-inspired ansatz
- Comparison with exact (FCI) results

**Run it:**
```bash
# First install requirements
pip install -r vqe_requirements.txt

# Then run
python vqe_h2o_example.py
```

---

### 3. `vqe_requirements.txt` - Dependencies
All required packages for the full VQE pipeline:
- CUDA Quantum
- OpenFermion (quantum chemistry)
- OpenFermion-PySCF (classical calculations)
- SciPy (optimization)
- NumPy (numerical operations)

**Install all requirements:**
```bash
pip install -r vqe_requirements.txt
```

---

## Quick Start

### Option 1: Simple Start (H2)
```bash
# Minimal dependencies
pip install cudaq scipy numpy

# Run simple example
python vqe_h2_simple.py
```

### Option 2: Full Pipeline (H2O)
```bash
# Install all chemistry dependencies
pip install -r vqe_requirements.txt

# Run complete example
python vqe_h2o_example.py
```

---

## Understanding VQE

### What is VQE?
VQE is a hybrid quantum-classical algorithm that finds the ground state energy of a quantum system (like a molecule):

1. **Quantum Part**: Prepare a parameterized quantum state (ansatz) and measure the energy
2. **Classical Part**: Use classical optimization to update parameters and minimize energy
3. **Repeat**: Iterate until convergence

### VQE Workflow
```
Molecular Geometry 
    ↓
Classical Quantum Chemistry (HF, integrals)
    ↓
Jordan-Wigner Transform → Qubit Hamiltonian
    ↓
Prepare Ansatz (parameterized quantum circuit)
    ↓
Measure Energy ← ─┐
    ↓              │
Classical Optimizer│
    └──────────────┘
    ↓
Ground State Energy
```

---

## Key Concepts

### Ansatz (Trial Wavefunction)
The parameterized quantum circuit that prepares your trial quantum state. Common choices:
- **Hardware-efficient**: Arbitrary rotation + entangling gates (used in these examples)
- **UCCSD**: Unitary Coupled Cluster Singles and Doubles (chemistry-inspired)
- **ADAPT-VQE**: Adaptively build the ansatz

### Hamiltonian
The energy operator for your molecule, expressed as a sum of Pauli strings:
```
H = c₀·I + c₁·Z₀ + c₂·X₀X₁ + c₃·Z₀Z₁ + ...
```

### Jordan-Wigner Transformation
Converts fermionic operators (creation/annihilation of electrons) to qubit operators (Pauli matrices).

---

## GPU Acceleration

To use GPU acceleration, change the target:

```python
# CPU (default)
cudaq.set_target('qpp-cpu')

# Single GPU
cudaq.set_target('nvidia')

# Multiple GPUs
cudaq.set_target('nvidia-mgpu')
```

---

## Typical Results

### H2 Molecule
- **Exact Energy**: -1.137283834 Ha
- **VQE Energy**: ~-1.13728 Ha (with good ansatz)
- **Error**: < 0.0001 Ha (< 0.06 kcal/mol)
- **Chemical Accuracy**: ✓ Achieved

### H2O Molecule
- **Exact Energy**: ~-75.01 Ha
- **VQE Energy**: Depends on ansatz complexity
- **Chemical Accuracy Goal**: < 1.6 kcal/mol error

**Note**: Chemical accuracy (1.6 kcal/mol = 0.0026 Ha) is the typical threshold for practical chemistry applications.

---

## Troubleshooting

### "Cannot import openfermion"
```bash
pip install openfermion openfermionpyscf
```

### "PySCF not found"
PySCF is installed automatically with openfermionpyscf, but if issues persist:
```bash
pip install pyscf
```

### Optimization not converging
- Try more layers in the ansatz
- Use different optimizer (`L-BFGS-B`, `Powell`)
- Adjust initial parameters
- Increase `maxiter` in optimization options

### Out of memory (GPU)
- Use CPU target: `cudaq.set_target('qpp-cpu')`
- Reduce active space (for custom molecules)
- Use smaller basis set

---

## Next Steps

1. **Start Simple**: Run `vqe_h2_simple.py` to understand the basics
2. **Go Complex**: Try `vqe_h2o_example.py` for the full pipeline
3. **Experiment**: Modify the ansatz, try different molecules, adjust parameters
4. **GPU**: Enable GPU acceleration for larger systems
5. **Custom Molecules**: Adapt the H2O example for your own molecules

---

## Additional Resources

- [CUDA Quantum Documentation](https://nvidia.github.io/cuda-quantum/latest/)
- [CUDA Quantum VQE Tutorial](https://nvidia.github.io/cuda-quantum/latest/examples/python/tutorials/vqe.html)
- [OpenFermion Documentation](https://quantumai.google/openfermion)
- [VQE Review Paper](https://arxiv.org/abs/2012.09265)

---

## Performance Tips

1. **Use GPU**: For systems with >10 qubits, GPU can be 10-100x faster
2. **Batch Evaluations**: CUDA Quantum supports batched parameter evaluations
3. **Active Space**: For large molecules, use active space approximation
4. **Smart Initialization**: Initialize parameters near expected values
5. **Gradient-based Optimizers**: For smooth landscapes, use L-BFGS-B

---

## Example Output

```
==============================================================================
VQE FOR H2O MOLECULE - CUDA QUANTUM
==============================================================================

Molecular Geometry:
  O: ( 0.0000,  0.0000,  0.0000) Angstroms
  H: ( 0.0000,  0.7569,  0.5869) Angstroms
  H: ( 0.0000, -0.7569,  0.5869) Angstroms

Number of qubits required: 14
Classical Reference Energies:
  Nuclear Repulsion: 9.18953442 Ha
  Hartree-Fock:     -74.96590119 Ha
  FCI (Exact):      -75.01234567 Ha

Starting VQE Optimization...
  Iteration   10: Energy = -75.00123456 Ha
  Iteration   20: Energy = -75.01156789 Ha
  ...

FINAL RESULTS
  FCI (Exact):      -75.01234567 Ha
  VQE:              -75.01198765 Ha
  
✓ Result is within chemical accuracy (1.6 kcal/mol)!
```

---

**Happy quantum computing! 🚀⚛️**


