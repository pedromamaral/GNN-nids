"""
Adversarial attack implementations for GNN-based NIDS.

Features:
- FGSM (Fast Gradient Sign Method): single-step attack
- PGD (Projected Gradient Descent): iterative attack with projection
- Construction-aware PGD: rebuilds the k-NN graph from the perturbed features
  at every step (the adaptive attacker for feature-derived graphs)
- All support selective node attacks (malicious nodes only) and an optional
  attacker-controllable feature mask
- Feature clipping and bounded perturbations
"""

from .fgsm import fgsm_attack
from .pgd import pgd_attack
from .construction_aware import construction_aware_pgd

__all__ = ["fgsm_attack", "pgd_attack", "construction_aware_pgd"]
