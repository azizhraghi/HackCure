"""Build immutable, versioned Twin snapshots and keep them."""

import hashlib
import json
from datetime import datetime

from .dimensions import ANALYSIS_DIMENSIONS, _latest_by_type, build_context, build_dimensions
from .models import RecomputeReason, TwinInputs, TwinSnapshot

TWIN_VERSION = "twin-0.1.0"


class StaleInputError(Exception):
    """The inputs are older than what the previous snapshot already used."""


class VersionConflictError(Exception):
    """Another job already wrote this version; rebuild on top of the latest."""


def build_snapshot(
    inputs: TwinInputs,
    as_of: datetime,
    previous: TwinSnapshot | None = None,
    reason: RecomputeReason | None = None,
) -> TwinSnapshot:
    """Build the next snapshot for an episode.

    Returns `previous` unchanged when nothing it describes has changed, so
    replays and repeated rebuilds do not create new versions.
    """
    dims, evidence = build_dimensions(inputs, as_of)
    context, context_evidence = build_context(inputs.protocol, inputs.dossier, inputs.episode.episode_id)
    evidence = evidence + context_evidence
    protocol_version = inputs.protocol.version if inputs.protocol else None

    times = [r.received_at for r in (*inputs.symptom_reports, *inputs.medication_reports)]
    times += [a.input_watermark or a.created_at for a in inputs.analyses]
    watermark = max(times, default=None)
    if previous and previous.input_watermark and (
        watermark is None or watermark < previous.input_watermark
    ):
        raise StaleInputError("inputs end before the previous snapshot's watermark")

    latest = _latest_by_type(inputs.analyses)
    pipeline_versions = {"twin": TWIN_VERSION} | {
        ANALYSIS_DIMENSIONS[t]: a.model_version for t, a in sorted(latest.items())
    }

    expected = sorted(inputs.expected, key=lambda t: t.metric)
    limitations = ["Dimensions are reported separately; there is no overall recovery score."]
    if expected:
        origin = ", ".join(sorted({t.data_origin for t in expected}))
        pipeline_versions["trajectory_model"] = expected[0].model_version
        limitations.append(
            f"Expected trajectories are model predictions learned from {origin} patient "
            "data; they are not clinically validated."
        )
    else:
        limitations.append("No expected trajectory was supplied.")
    forecasts = sorted(inputs.forecasts, key=lambda f: (f.target_code, f.horizon_hours))
    if forecasts:
        limitations.append(
            "Forecasts are supplementary estimates; they never replace a safety decision.")
    if protocol_version is None:
        limitations.append("No active approved protocol; no expectations are shown.")

    body = {
        "episode_id": inputs.episode.episode_id,
        "protocol_version": protocol_version,
        "context": context.model_dump(mode="json"),
        "dimensions": [d.model_dump(mode="json") for d in dims],
        "expected": [t.model_dump(mode="json") for t in expected],
        "forecasts": [f.model_dump(mode="json") for f in forecasts],
        "evidence": [e.model_dump(mode="json") for e in evidence],
        "pipeline_versions": pipeline_versions,
    }
    content_hash = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()
    if previous and previous.content_hash == content_hash:
        return previous

    changed = [
        d.name for d in dims
        if previous is None or d != previous.dimension(d.name)
    ]
    if reason is None:
        if previous is None:
            reason = "initial"
        elif previous.protocol_version != protocol_version:
            reason = "protocol_change"
        elif changed == ["recovery_timeline"]:
            reason = "time_advanced"
        else:
            reason = "new_input"

    version = previous.snapshot_version + 1 if previous else 1
    return TwinSnapshot(
        snapshot_id=f"snap_{inputs.episode.episode_id}_v{version}_{content_hash[:8]}",
        snapshot_version=version,
        patient_id=inputs.episode.patient_id,
        episode_id=inputs.episode.episode_id,
        as_of=as_of,
        input_watermark=watermark,
        protocol_version=protocol_version,
        context=context,
        dimensions=dims,
        expected_trajectories=expected,
        forecasts=forecasts,
        evidence=evidence,
        limitations=limitations,
        pipeline_versions=pipeline_versions,
        recompute_reason=reason,
        changed_dimensions=changed,
        previous_snapshot_id=previous.snapshot_id if previous else None,
        content_hash=content_hash,
    )


class TwinStore:
    """Append-only snapshot history per episode (in memory for now).

    Old snapshots are never modified or removed, so an investigation that
    cites a snapshot_id can always read back exactly what it saw.
    """

    def __init__(self) -> None:
        self._by_episode: dict[str, list[TwinSnapshot]] = {}
        self._by_id: dict[str, TwinSnapshot] = {}

    def latest(self, episode_id: str) -> TwinSnapshot | None:
        history = self._by_episode.get(episode_id)
        return history[-1] if history else None

    def get(self, snapshot_id: str) -> TwinSnapshot | None:
        return self._by_id.get(snapshot_id)

    def history(self, episode_id: str) -> list[TwinSnapshot]:
        return list(self._by_episode.get(episode_id, []))

    def append(self, snapshot: TwinSnapshot) -> None:
        history = self._by_episode.setdefault(snapshot.episode_id, [])
        if snapshot.snapshot_version != len(history) + 1:
            raise VersionConflictError(
                f"expected version {len(history) + 1}, got {snapshot.snapshot_version}"
            )
        history.append(snapshot)
        self._by_id[snapshot.snapshot_id] = snapshot

    def update(
        self, inputs: TwinInputs, as_of: datetime, reason: RecomputeReason | None = None
    ) -> TwinSnapshot:
        """Rebuild from the latest snapshot and store the result if it is new."""
        previous = self.latest(inputs.episode.episode_id)
        snapshot = build_snapshot(inputs, as_of, previous, reason)
        if snapshot is not previous:
            self.append(snapshot)
        return snapshot
