"""
Joint shaping + decoy-injection attack on context detectors (CTU-13, E017 / D17).

The attacker is every infected host at once. It controls its own botnet flows
(shaping: raw Dur, TotPkts, SrcBytes may only increase) and may emit decoy flows
from itself to benign destinations (injection). Both cost extra bytes, drawn
from one budget per (window, bot host):

    budget = beta * (bytes of the host's botnet flows in the window)
    shaping gets (1 - rho) * budget, decoys get rho * budget.

Everything is done on raw Argus fields and mapped to the 36 standardised
features with a differentiable copy of ``Ctu13Preprocessor.raw_features`` (only
the six volume columns change). Context features (per-window same-source /
same-destination means + log count, as in 00 ``--context host``) and the
endpoint graph (E-GraphSAGE, node key = IP) are recomputed after the attack,
with decoys as extra members of the bot's source group, the destination's
group, or extra edges.
"""

from dataclasses import dataclass
from typing import Callable, Dict, Optional

import numpy as np
import pandas as pd
import torch

N_VOLUME = 6          # standardised columns: log Dur, TotPkts, TotBytes, SrcBytes, DstBytes, BytesPerPkt
MIN_PKT_BYTES = 60    # smallest packet an added packet can be
MTU = 1500
DECOY_MIN_SRC = 60    # a decoy has at least one outgoing packet


@dataclass
class Chunk:
    """Consecutive whole windows of the test flows (detector-specific window size)."""
    X: np.ndarray          # (n, 36) clean standardised features
    raw: np.ndarray        # (n, 4) float64: Dur, TotPkts, TotBytes, SrcBytes
    y: np.ndarray          # (n,) 1 = botnet
    src_key: np.ndarray    # (n,) int64 source host
    dst_key: np.ndarray    # (n,) int64 destination host
    win: np.ndarray        # (n,) int64 window id, non-decreasing, unique across scenarios


@dataclass
class Context:
    """Group structure of a flow set (originals followed by decoys)."""
    gsrc: torch.Tensor
    gdst: torch.Tensor
    nsrc: int
    ndst: int
    edge_src: torch.Tensor   # endpoint-graph node ids (shared key space per window)
    edge_dst: torch.Tensor
    n_nodes: int


@dataclass
class Plan:
    bot: np.ndarray               # indices of botnet flows in the chunk
    g_bot: np.ndarray             # budget group of each botnet flow
    budget_shape: np.ndarray      # (G,) bytes
    budget_decoy: np.ndarray      # (G,) bytes
    base_bytes: np.ndarray        # (G,) clean botnet bytes of the group
    dec_group: np.ndarray         # (m,)
    dec_src_key: np.ndarray
    dec_dst_key: np.ndarray
    dec_win: np.ndarray
    dec_raw: np.ndarray           # (m, 4) Dur, TotPkts, TotBytes, SrcBytes of the template
    dec_cat: np.ndarray           # (m, 36 - N_VOLUME) copied categorical features


# ---------------------------------------------------------------- features

def volume_features(dur, pkts, tot, src, mean, scale):
    """Standardised volume columns from raw fields; mirrors Ctu13Preprocessor.raw_features."""
    dst = (tot - src).clamp(min=0)
    cols = [
        torch.log1p(dur.clamp(min=0)), torch.log1p(pkts.clamp(min=0)), torch.log1p(tot.clamp(min=0)),
        torch.log1p(src.clamp(min=0)), torch.log1p(dst), torch.log1p(tot.clamp(min=0) / pkts.clamp(min=1)),
    ]
    return (torch.stack(cols, dim=1) - mean[:N_VOLUME]) / scale[:N_VOLUME]


def host_context_t(X: torch.Tensor, ctx: Context) -> torch.Tensor:
    """Torch twin of 00 host_context: [X, src mean, log1p src count, dst mean, log1p dst count]."""
    out = [X]
    for g, n in ((ctx.gsrc, ctx.nsrc), (ctx.gdst, ctx.ndst)):
        counts = torch.bincount(g, minlength=n).clamp(min=1).to(X.dtype)
        sums = torch.zeros(n, X.shape[1], dtype=X.dtype, device=X.device).index_add_(0, g, X)
        out.append((sums / counts[:, None])[g])
        out.append(torch.log1p(counts)[g][:, None])
    return torch.cat(out, dim=1)


def make_context(src_key, dst_key, win, device) -> Context:
    """Group codes per (window, host) for src and dst, node ids per (window, host) for the graph."""
    src_key, dst_key, win = (np.asarray(a, dtype=np.int64) for a in (src_key, dst_key, win))
    all_codes = pd.factorize(np.concatenate([src_key, dst_key]))[0].astype(np.int64)
    k = int(all_codes.max()) + 1 if all_codes.size else 1
    n = src_key.size
    s_code, d_code = all_codes[:n], all_codes[n:]
    gsrc = pd.factorize(win * k + s_code)[0]
    gdst = pd.factorize(win * k + d_code)[0]
    nodes = pd.factorize(np.concatenate([win * k + s_code, win * k + d_code]))[0]
    t = lambda a: torch.as_tensor(np.asarray(a, dtype=np.int64), device=device)  # noqa: E731
    return Context(t(gsrc), t(gdst), int(gsrc.max()) + 1 if n else 0, int(gdst.max()) + 1 if n else 0,
                   t(nodes[:n]), t(nodes[n:]), int(nodes.max()) + 1 if n else 0)


# ---------------------------------------------------------------- projections

def project_shaping(dsrc, dpkts, ddur, raw, g, budget, delay_ok=None):
    """Feasible raw increases: budget per group, 60 B per added packet, <= MTU per packet, Dur <= doubled.

    ``delay_ok`` (bool per flow) says where delay is allowed; default: only where the group has a
    shaping budget (delay 'coupled' to shaping, the E017 pilot behaviour).
    """
    dur, pkts, _, src = raw.unbind(1)
    dsrc = dsrc.clamp(min=0)
    spent = torch.zeros_like(budget).index_add_(0, g, dsrc)
    scale = torch.where(spent > budget, budget / spent.clamp(min=1e-9), torch.ones_like(spent))
    dsrc = dsrc * scale[g]
    hi = dsrc / MIN_PKT_BYTES
    lo = torch.minimum(((src + dsrc) / MTU - pkts).clamp(min=0), hi)
    dpkts = torch.maximum(torch.minimum(dpkts, hi), lo)
    ok = (budget[g] > 0) if delay_ok is None else delay_ok
    return dsrc, dpkts, ddur.clamp(min=0).minimum(dur) * ok


def integerize_shaping(dsrc, dpkts, ddur, raw):
    """Whole bytes and packets (floor/round, kept feasible) for evaluation."""
    _, pkts, _, src = raw.unbind(1)
    dsrc = torch.floor(dsrc)
    hi = torch.floor(dsrc / MIN_PKT_BYTES)
    lo = torch.minimum(torch.ceil(((src + dsrc) / MTU - pkts).clamp(min=0)), hi)
    dpkts = torch.maximum(torch.minimum(torch.round(dpkts), hi), lo)
    return dsrc, dpkts, ddur


def project_decoys(dur, pkts, src, dst_t, dur_t, g, budget):
    """Decoy volumes: >= 1 packet of >= 60 B, <= MTU per packet, total bytes within the group budget."""
    src = src.clamp(min=DECOY_MIN_SRC)
    extra = (src - DECOY_MIN_SRC)
    floor_cost = torch.zeros_like(budget).index_add_(0, g, dst_t + DECOY_MIN_SRC)
    room = (budget - floor_cost).clamp(min=0)
    extra_sum = torch.zeros_like(budget).index_add_(0, g, extra)
    scale = torch.where(extra_sum > room, room / extra_sum.clamp(min=1e-9), torch.ones_like(room))
    src = DECOY_MIN_SRC + extra * scale[g]
    tot = src + dst_t
    hi = (tot / MIN_PKT_BYTES).clamp(min=1)
    lo = torch.minimum((tot / MTU).clamp(min=1), hi)
    return dur.clamp(min=0).minimum(2 * dur_t + 1.0), torch.maximum(torch.minimum(pkts, hi), lo), src


def integerize_decoys(dur, pkts, src, dst_t):
    src = torch.floor(src)
    tot = src + dst_t
    hi = torch.floor(tot / MIN_PKT_BYTES).clamp(min=1)
    lo = torch.minimum(torch.ceil(tot / MTU).clamp(min=1), hi)
    return dur, torch.maximum(torch.minimum(torch.round(pkts), hi), lo), src


# ---------------------------------------------------------------- planning

def build_plan(chunk: Chunk, beta: float, rho: float, rng: np.random.Generator,
               replay: bool = False, cap_mult: float = 1.0) -> Plan:
    """Budget groups (window, bot host) and the decoy slots each group can afford.

    Decoy candidates copy a random benign flow of the same window (destination
    sampled by frequency, categorical features copied). A candidate is accepted
    while the group's decoy budget covers the cheapest feasible version
    (dst reply bytes + one 60 B packet), or, for ``replay``, the unmodified flow.
    """
    bot = np.flatnonzero(chunk.y == 1)
    empty = np.zeros(0, dtype=np.int64)
    n_cat = chunk.X.shape[1] - N_VOLUME
    if bot.size == 0:
        z = np.zeros(0)
        return Plan(bot, empty, z, z, z, empty, empty, empty, empty, np.zeros((0, 4)), np.zeros((0, n_cat), np.float32))
    codes = pd.factorize(chunk.src_key[bot])[0].astype(np.int64)
    g_bot = pd.factorize(chunk.win[bot] * (int(codes.max()) + 1) + codes)[0]
    n_g = int(g_bot.max()) + 1
    tot = chunk.raw[bot, 2]
    base = np.bincount(g_bot, weights=tot, minlength=n_g)
    first = np.zeros(n_g, dtype=np.int64)
    first[g_bot[::-1]] = np.arange(bot.size)[::-1]           # first botnet flow of each group
    g_win, g_key = chunk.win[bot][first], chunk.src_key[bot][first]
    budget = beta * base
    b_shape, b_decoy = (1.0 - rho) * budget, rho * budget

    dec = dict(group=empty, tpl=empty)
    if rho > 0:
        benign = np.flatnonzero(chunk.y == 0)
        bw = chunk.win[benign]
        lo, hi = np.searchsorted(bw, g_win, "left"), np.searchsorted(bw, g_win, "right")
        cap = np.where(hi > lo, np.ceil(cap_mult * np.bincount(g_bot, minlength=n_g)).astype(np.int64), 0)
        cand_g = np.repeat(np.arange(n_g), cap)
        tpl = benign[lo[cand_g] + np.floor(rng.random(cand_g.size) * (hi - lo)[cand_g]).astype(np.int64)]
        raw = chunk.raw[tpl]
        dst_t = np.maximum(raw[:, 2] - raw[:, 3], 0)
        cost = dst_t + (np.maximum(raw[:, 3], DECOY_MIN_SRC) if replay else DECOY_MIN_SRC)
        cs = np.cumsum(cost) if cost.size else np.zeros(1)
        start = np.searchsorted(cand_g, np.arange(n_g))
        offset = np.where(start > 0, cs[np.maximum(start - 1, 0)], 0.0)
        keep = (cs - offset[cand_g]) <= b_decoy[cand_g]
        dec = dict(group=cand_g[keep], tpl=tpl[keep])
    g, t = dec["group"], dec["tpl"]
    return Plan(bot, g_bot, b_shape, b_decoy, base, g, g_key[g], chunk.dst_key[t], g_win[g],
                chunk.raw[t], chunk.X[t][:, N_VOLUME:])


# ---------------------------------------------------------------- attack

LogitFn = Callable[[torch.Tensor, Context], torch.Tensor]


def assemble(chunk: Chunk, plan: Plan, shape, decoy, mean, scale, tX, traw, tcat, tdst, tdur):
    """Perturbed features: originals (n, 36) followed by decoys (m, 36). Differentiable in shape/decoy."""
    X = tX
    if plan.bot.size:
        dsrc, dpkts, ddur = shape
        bot = torch.as_tensor(plan.bot, device=X.device)
        dur, pkts, tot, src = traw[bot].unbind(1)
        vol = volume_features(dur + ddur, pkts + dpkts, tot + dsrc, src + dsrc, mean, scale)
        X = X.index_put((bot,), torch.cat([vol.to(X.dtype), X[bot, N_VOLUME:]], dim=1))
    if decoy is not None and tcat.shape[0]:
        d_dur, d_pkts, d_src = decoy
        vol = volume_features(d_dur, d_pkts, d_src + tdst, d_src, mean, scale)
        X = torch.cat([X, torch.cat([vol.to(X.dtype), tcat], dim=1)], dim=0)
    return X


def _attack_once(chunk: Chunk, plan: Plan, logit_fn: Optional[LogitFn], thr_logit: float, mean, scale,
               rng: np.random.Generator, device, steps: int = 30, step_frac: float = 0.2,
               optimise: bool = True, delay: str = "coupled") -> Dict[str, object]:
    """Optimise (or only initialise) the attack against ``logit_fn``; return integerised perturbed flows.

    ``logit_fn(features, ctx)`` must return one logit per row (originals first). With
    ``optimise=False`` (or no botnet flows) shaping stays at zero and decoys at their template.
    """
    f32 = dict(dtype=torch.float32, device=device)
    f64 = dict(dtype=torch.float64, device=device)   # byte counts need exact integers
    n, m, nb = len(chunk.y), len(plan.dec_group), len(plan.bot)
    tX = torch.as_tensor(chunk.X, **f32)
    traw = torch.as_tensor(chunk.raw, **f64)
    tcat = torch.as_tensor(plan.dec_cat, **f32)
    draw = torch.as_tensor(plan.dec_raw, **f64)
    d_dur_t, d_pkts_t, d_tot_t, d_src_t = draw.unbind(1) if m else (traw[:0, 0],) * 4
    d_dst_t = (d_tot_t - d_src_t).clamp(min=0)
    ctx = make_context(np.concatenate([chunk.src_key, plan.dec_src_key]),
                       np.concatenate([chunk.dst_key, plan.dec_dst_key]),
                       np.concatenate([chunk.win, plan.dec_win]), device)
    g_bot = torch.as_tensor(plan.g_bot, device=device)
    g_dec = torch.as_tensor(plan.dec_group, device=device)
    b_shape = torch.as_tensor(plan.budget_shape, **f64)
    b_decoy = torch.as_tensor(plan.budget_decoy, **f64)
    n_g_bot = torch.bincount(g_bot, minlength=len(plan.budget_shape)).clamp(min=1).to(torch.float64) if nb else None
    n_g_dec = torch.bincount(g_dec, minlength=len(plan.budget_shape)).clamp(min=1).to(torch.float64) if m else None

    raw_bot = traw[torch.as_tensor(plan.bot, device=device)] if nb else traw[:0]
    zero = torch.zeros(nb, **f64)
    share = (b_shape / n_g_bot)[g_bot] if nb else zero      # bytes each botnet flow can add on average
    s_scale = [share, share / 100.0, raw_bot[:, 0].clamp(min=0.1)] if nb else [zero] * 3
    u = torch.as_tensor(rng.random((3, nb)), **f64)
    delay_ok = {"coupled": None, "free": torch.ones(nb, dtype=torch.bool, device=device),
                "off": torch.zeros(nb, dtype=torch.bool, device=device)}[delay]
    shape = list(project_shaping(u[0] * share, u[1] * share / 100.0, u[2] * raw_bot[:, 0], raw_bot, g_bot, b_shape, delay_ok)) if nb else [zero] * 3
    if m:
        d_share = (b_decoy / n_g_dec)[g_dec]
        d_scale = [d_share, d_share / 100.0, d_dur_t.clamp(min=0.1)]
        decoy = list(project_decoys(d_dur_t, d_pkts_t, d_src_t, d_dst_t, d_dur_t, g_dec, b_decoy))
    else:
        decoy = None

    def features(shp, dcy):
        return assemble(chunk, plan, shp, dcy, mean, scale, tX, traw, tcat, d_dst_t, d_dur_t)

    if optimise and logit_fn is not None and nb and (float(b_shape.sum()) > 0 or m or delay == "free"):
        bot_t = torch.as_tensor(plan.bot, device=device)
        state = shape + (decoy or [])
        scales = s_scale + (d_scale if decoy else [])
        for _ in range(steps):
            vs = [v.detach().requires_grad_(True) for v in state]
            logit = logit_fn(features(vs[:3], vs[3:] or None), ctx)[bot_t]
            loss = torch.nn.functional.softplus(logit - thr_logit).mean()
            grads = torch.autograd.grad(loss, vs)
            vs = [v.detach() - step_frac * s * g.sign() for v, s, g in zip(vs, scales, grads)]
            state = list(project_shaping(*vs[:3], raw_bot, g_bot, b_shape, delay_ok))
            if decoy:
                state += list(project_decoys(*vs[3:], d_dst_t, d_dur_t, g_dec, b_decoy))
        shape, decoy = state[:3], (state[3:] or None)

    if nb:
        shape = list(integerize_shaping(*shape, raw_bot))
    if decoy:
        decoy = list(integerize_decoys(*decoy, d_dst_t))
    with torch.no_grad():
        X = features(shape, decoy)
    return {
        "X": X, "ctx": ctx, "n": n, "m": m,
        "cost_shape": float(shape[0].sum()) if nb else 0.0,
        "cost_decoy": float((decoy[2] + d_dst_t).sum()) if m else 0.0,
        "group_shape": torch.zeros(len(plan.budget_shape), dtype=torch.float64, device=device).index_add_(0, g_bot, shape[0]) if nb else None,
        "group_decoy": torch.zeros(len(plan.budget_shape), dtype=torch.float64, device=device).index_add_(0, g_dec, decoy[2] + d_dst_t) if m else None,
    }


def run_attack(chunk: Chunk, plan: Plan, logit_fn: Optional[LogitFn], thr_logit: float, mean, scale,
               rng: np.random.Generator, device, steps: int = 30, step_frac: float = 0.2,
               optimise: bool = True, delay: str = "coupled", restarts: int = 1) -> Dict[str, object]:
    """``_attack_once`` with ``restarts`` random initialisations; keeps the one with the lowest mean botnet loss.

    delay: 'coupled' (delay only where the group has a shaping budget; E017 pilot), 'free'
    (delay always allowed, also with rho = 1 and beta = 0: the delay-only attacker), 'off' (bytes only).
    """
    if delay not in ("coupled", "free", "off"):
        raise ValueError(f"delay must be coupled, free or off, got {delay!r}")
    best, best_obj = None, None
    for _ in range(max(restarts, 1) if optimise and logit_fn is not None else 1):
        res = _attack_once(chunk, plan, logit_fn, thr_logit, mean, scale, rng, device, steps, step_frac, optimise, delay)
        if restarts <= 1 or logit_fn is None or not len(plan.bot):
            return res
        with torch.no_grad():
            bot = torch.as_tensor(plan.bot, device=device)
            obj = float(torch.nn.functional.softplus(logit_fn(res["X"], res["ctx"])[bot] - thr_logit).mean())
        if best is None or obj < best_obj:
            best, best_obj = res, obj
    return best
