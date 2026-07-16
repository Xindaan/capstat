"""Compute endpoints: one per capstat-core entry point.

Each handler is a three-line adapter -- validate input shape (Pydantic),
call the core inside :func:`core_errors`, wrap the result in its mirror model.
No statistics happen here.
"""

from __future__ import annotations

from capstat_core import (
    ControlChart,
    ControlLimits,
    analyze_capability,
    bias,
    capability,
    cusum_chart,
    describe,
    ewma_chart,
    gage_rr,
    gage_rr_range,
    i_mr_chart,
    linearity,
    nelson_rules,
    stability,
    western_electric_rules,
    xbar_r_chart,
    xbar_s_chart,
)
from fastapi import APIRouter

from capstat_api.errors import core_errors
from capstat_api.requests import (
    AnalyzeCapabilityRequest,
    BiasRequest,
    CapabilityRequest,
    CusumRequest,
    DescriptiveRequest,
    EwmaRequest,
    GageRRRequest,
    IMRRequest,
    LinearityRequest,
    RulesRequest,
    StabilityRequest,
    SubgroupRequest,
)
from capstat_api.schemas import (
    BiasReportOut,
    CapabilityAnalysisOut,
    CapabilityReportOut,
    ChartPairOut,
    CusumChartOut,
    DescriptiveSummaryOut,
    EwmaChartOut,
    GageRRReportOut,
    LinearityReportOut,
    RuleViolationOut,
    StabilityReportOut,
)

router = APIRouter(prefix="/compute", tags=["compute"])


@router.post("/descriptive", response_model=DescriptiveSummaryOut)
def compute_descriptive(req: DescriptiveRequest) -> DescriptiveSummaryOut:
    with core_errors():
        result = describe(req.data)
    return DescriptiveSummaryOut.model_validate(result)


@router.post("/capability", response_model=CapabilityReportOut)
def compute_capability(req: CapabilityRequest) -> CapabilityReportOut:
    with core_errors():
        result = capability(
            req.data,
            lsl=req.lsl,
            usl=req.usl,
            target=req.target,
            within_method=req.within_method,
            alpha=req.alpha,
        )
    return CapabilityReportOut.model_validate(result)


@router.post("/capability/analyze", response_model=CapabilityAnalysisOut)
def compute_capability_analyze(
    req: AnalyzeCapabilityRequest,
) -> CapabilityAnalysisOut:
    with core_errors():
        result = analyze_capability(
            req.data,
            lsl=req.lsl,
            usl=req.usl,
            target=req.target,
            alpha=req.alpha,
        )
    return CapabilityAnalysisOut.model_validate(result)


@router.post("/gage-rr", response_model=GageRRReportOut)
def compute_gage_rr(req: GageRRRequest) -> GageRRReportOut:
    with core_errors():
        if req.method == "average_range":
            result = gage_rr_range(
                req.data,
                tolerance=req.tolerance,
                study_var_multiplier=req.study_var_multiplier,
            )
        else:
            result = gage_rr(
                req.data,
                tolerance=req.tolerance,
                study_var_multiplier=req.study_var_multiplier,
                interaction_alpha=req.interaction_alpha,
            )
    return GageRRReportOut.model_validate(result)


@router.post("/bias", response_model=BiasReportOut)
def compute_bias(req: BiasRequest) -> BiasReportOut:
    with core_errors():
        result = bias(req.measurements, req.reference, alpha=req.alpha)
    return BiasReportOut.model_validate(result)


@router.post("/linearity", response_model=LinearityReportOut)
def compute_linearity(req: LinearityRequest) -> LinearityReportOut:
    with core_errors():
        result = linearity(
            req.references,
            req.measurements,
            process_variation=req.process_variation,
            alpha=req.alpha,
        )
    return LinearityReportOut.model_validate(result)


@router.post("/stability", response_model=StabilityReportOut)
def compute_stability(req: StabilityRequest) -> StabilityReportOut:
    with core_errors():
        result = stability(req.measurements)
    return StabilityReportOut.model_validate(result)


@router.post("/control-chart/i-mr", response_model=ChartPairOut)
def compute_i_mr(req: IMRRequest) -> ChartPairOut:
    with core_errors():
        result = i_mr_chart(req.data)
    return ChartPairOut.model_validate(result)


@router.post("/control-chart/xbar-r", response_model=ChartPairOut)
def compute_xbar_r(req: SubgroupRequest) -> ChartPairOut:
    with core_errors():
        result = xbar_r_chart(req.subgroups)
    return ChartPairOut.model_validate(result)


@router.post("/control-chart/xbar-s", response_model=ChartPairOut)
def compute_xbar_s(req: SubgroupRequest) -> ChartPairOut:
    with core_errors():
        result = xbar_s_chart(req.subgroups)
    return ChartPairOut.model_validate(result)


@router.post("/control-chart/ewma", response_model=EwmaChartOut)
def compute_ewma(req: EwmaRequest) -> EwmaChartOut:
    with core_errors():
        result = ewma_chart(
            req.data,
            target=req.target,
            sigma=req.sigma,
            lmbda=req.lmbda,
            L=req.L,
            time_varying_limits=req.time_varying_limits,
        )
    return EwmaChartOut.model_validate(result)


@router.post("/control-chart/cusum", response_model=CusumChartOut)
def compute_cusum(req: CusumRequest) -> CusumChartOut:
    with core_errors():
        result = cusum_chart(
            req.data,
            target=req.target,
            sigma=req.sigma,
            k=req.k,
            h=req.h,
        )
    return CusumChartOut.model_validate(result)


def _chart_from_request(req: RulesRequest) -> ControlChart:
    """Rebuild the minimal chart the rule functions read (points + limits)."""
    return ControlChart(
        name="chart",
        points=tuple(req.points),
        limits=ControlLimits(
            center=req.limits.center,
            lower=req.limits.lower,
            upper=req.limits.upper,
        ),
        violations=(),
    )


@router.post("/rules/nelson", response_model=list[RuleViolationOut])
def compute_nelson_rules(req: RulesRequest) -> list[RuleViolationOut]:
    with core_errors():
        violations = nelson_rules(_chart_from_request(req), req.rules)
    return [RuleViolationOut.model_validate(v) for v in violations]


@router.post("/rules/western-electric", response_model=list[RuleViolationOut])
def compute_western_electric_rules(req: RulesRequest) -> list[RuleViolationOut]:
    with core_errors():
        violations = western_electric_rules(_chart_from_request(req), req.rules)
    return [RuleViolationOut.model_validate(v) for v in violations]
