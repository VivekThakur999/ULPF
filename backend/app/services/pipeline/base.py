"""Pipeline stage abstraction and the runner."""
from __future__ import annotations

import time
from abc import ABC, abstractmethod

from app.core.logging import get_logger
from app.services.pipeline.context import (
    STAGE_ERROR,
    PipelineContext,
    StageResult,
)

log = get_logger("pipeline")


class PipelineStage(ABC):
    name: str = "stage"

    @abstractmethod
    def run(self, ctx: PipelineContext, result: StageResult) -> None:
        """Mutate ctx; annotate result. Raising is caught and recorded."""

    def apply(self, ctx: PipelineContext) -> StageResult:
        result = StageResult(stage=self.name)
        start = time.perf_counter()
        try:
            self.run(ctx, result)
        except Exception as exc:  # never let one stage crash the pipeline
            result.status = STAGE_ERROR
            result.errors.append(f"{type(exc).__name__}: {exc}")
            log.exception("stage %s failed on line %d", self.name, ctx.line_number)
        finally:
            result.duration_ms = (time.perf_counter() - start) * 1000
        ctx.add(result)
        return result


class Pipeline:
    def __init__(self, stages: list[PipelineStage]):
        self.stages = stages

    def run(self, ctx: PipelineContext) -> PipelineContext:
        for stage in self.stages:
            stage.apply(ctx)
            if ctx.dropped:
                break
        return ctx

    @property
    def stage_names(self) -> list[str]:
        return [s.name for s in self.stages]
