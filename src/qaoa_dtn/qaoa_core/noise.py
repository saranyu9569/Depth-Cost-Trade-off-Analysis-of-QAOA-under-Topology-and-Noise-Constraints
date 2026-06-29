from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NoiseSetting:
    name: str
    depol_1q: float = 0.0
    depol_2q: float = 0.0
    readout: float = 0.0


def build_aer_simulator(setting: NoiseSetting, seed: int):
    try:
        from qiskit_aer import AerSimulator
        from qiskit_aer.noise import NoiseModel, depolarizing_error, ReadoutError
    except Exception as exc:
        raise ImportError("qiskit-aer is required for noisy simulation. Install with: pip install qiskit-aer") from exc

    noise_model = NoiseModel()

    if setting.depol_1q and setting.depol_1q > 0:
        err_1q = depolarizing_error(float(setting.depol_1q), 1)
        noise_model.add_all_qubit_quantum_error(err_1q, ["sx", "x"])

    if setting.depol_2q and setting.depol_2q > 0:
        err_2q = depolarizing_error(float(setting.depol_2q), 2)
        noise_model.add_all_qubit_quantum_error(err_2q, ["cx"])

    if setting.readout and setting.readout > 0:
        ro = float(setting.readout)
        readout = ReadoutError([[1.0 - ro, ro], [ro, 1.0 - ro]])
        noise_model.add_all_qubit_readout_error(readout)

    # No custom backend is passed into transpile. The simulator only executes
    # already-transpiled circuits. This avoids Qiskit version-specific conflicts
    # between backend basis, coupling maps, and 3-qubit gates.
    simulator = AerSimulator(noise_model=noise_model if len(noise_model.to_dict().get("errors", [])) else None)
    basis_gates = ["rz", "sx", "x", "cx", "measure"]
    return simulator, basis_gates
