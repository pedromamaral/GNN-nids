"""
PGD (Projected Gradient Descent) adversarial attack for PyTorch Geometric graphs.

Iterative feature-space evasion attack: applies multiple FGSM-like steps with
projection back into an L-inf epsilon-ball around the original features.

Notes on the attack configuration
---------------------------------
With a sign-based update of fixed size ``alpha``, each masked coordinate moves
by exactly ``alpha`` per step, so the boundary of the epsilon-ball is reached
after ``ceil(epsilon / alpha)`` steps.  If ``alpha`` is too small relative to
``epsilon`` the attack cannot traverse the ball; if it is too large the attack
saturates on the first step and degenerates to FGSM.  Following Madry et al.,
the default step size is ``alpha = 2.5 * epsilon / steps``, which lets the
attack cross the ball roughly 2.5 times and therefore actually re-estimate the
gradient direction along the way.  A random start inside the ball is enabled by
default for the same reason.
"""

from typing import Optional
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.data import Data


def default_step_size(epsilon: float, steps: int) -> float:
    """Standard PGD step size heuristic (Madry et al.): 2.5 * epsilon / steps."""
    return 2.5 * float(epsilon) / float(steps)


def pgd_attack(
    model: nn.Module,
    data: Data,
    epsilon: float = 0.05,
    alpha: Optional[float] = None,
    steps: int = 10,
    attack_only_malicious: bool = True,
    clip_min: Optional[float] = None,
    clip_max: Optional[float] = None,
    random_start: bool = True,
    generator: Optional[torch.Generator] = None,
) -> Data:
    """
    Apply a PGD attack to the node features of a PyTorch Geometric graph.

    Args:
        model: A GNN model (e.g., GCN_NIDS, GAT_NIDS).
        data: PyG Data object with ``x``, ``edge_index`` and ``y``
            (binary labels, 0 = benign, 1 = malicious).
        epsilon: L-inf bound on the perturbation.
        alpha: Step size.  If ``None`` (recommended), ``2.5 * epsilon / steps``
            is used.  Passing an explicit value that is much larger than
            ``epsilon / steps`` makes PGD collapse onto FGSM.
        steps: Number of PGD iterations.
        attack_only_malicious: If True, only perturb nodes where ``y == 1``.
        clip_min / clip_max: Optional bounds applied to the adversarial
            features after every step (feature-domain validity).
        random_start: If True, initialise the perturbation uniformly at random
            inside the epsilon-ball instead of starting at the clean point.
        generator: Optional ``torch.Generator`` for a reproducible random start.

    Returns:
        A new Data object with adversarial node features.  ``edge_index``,
        ``y`` and all other attributes are preserved.

    Raises:
        ValueError: If ``epsilon``, ``alpha`` or ``steps`` are not positive.
    """
    if epsilon <= 0:
        raise ValueError(f"epsilon must be positive, got {epsilon}")
    if steps <= 0:
        raise ValueError(f"steps must be positive, got {steps}")

    if alpha is None:
        alpha = default_step_size(epsilon, steps)
    if alpha <= 0:
        raise ValueError(f"alpha must be positive, got {alpha}")

    model.eval()

    device = data.x.device
    x_original = data.x.detach().clone()

    # Build the attack mask once (rows that are allowed to move).
    if attack_only_malicious:
        node_mask = data.y == 1
        if node_mask.sum() == 0:
            return data.clone()
    else:
        node_mask = torch.ones(data.num_nodes, dtype=torch.bool, device=device)

    x_adv = x_original.clone()

    if random_start:
        noise = torch.empty_like(x_original).uniform_(-epsilon, epsilon, generator=generator)
        x_adv[node_mask] = x_original[node_mask] + noise[node_mask]
        if clip_min is not None:
            x_adv = torch.clamp(x_adv, min=clip_min)
        if clip_max is not None:
            x_adv = torch.clamp(x_adv, max=clip_max)

    for _ in range(steps):
        x_adv = x_adv.detach().to(device).requires_grad_(True)

        data_adv = data.clone()
        data_adv.x = x_adv

        with torch.enable_grad():
            logits = model(data_adv)
            loss = F.cross_entropy(logits[node_mask], data.y[node_mask])

            model.zero_grad(set_to_none=True)
            loss.backward()
            grad_sign = x_adv.grad.sign()

        with torch.no_grad():
            x_updated = x_adv.detach().clone()
            x_updated[node_mask] = x_updated[node_mask] + alpha * grad_sign[node_mask]

            # Project back into the L-inf epsilon-ball around the clean features.
            perturbation = torch.clamp(x_updated - x_original, min=-epsilon, max=epsilon)
            x_adv = x_original + perturbation

            if clip_min is not None:
                x_adv = torch.clamp(x_adv, min=clip_min)
            if clip_max is not None:
                x_adv = torch.clamp(x_adv, max=clip_max)

    data_adv = data.clone()
    data_adv.x = x_adv.detach()
    return data_adv
