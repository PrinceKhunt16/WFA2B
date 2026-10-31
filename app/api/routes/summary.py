from fastapi import APIRouter, Depends

from app.api.dependencies import get_data_service
from app.schemas.accuracy import SummaryResponse
from app.services.data_service import DataService

router = APIRouter(prefix="/api/v1", tags=["summary"])


@router.get("/summary", response_model=SummaryResponse)
async def summary(service: DataService = Depends(get_data_service)) -> SummaryResponse:
    from app.api.routes.accuracy import accuracy

    metrics = await accuracy(
        start_date=service.settings.analysis_start_date,
        end_date=service.settings.analysis_end_date,
        decision_cutoff=None,
        service=service,
    )
    return SummaryResponse(
        evaluation_date_range=f"{metrics.start_date} to {metrics.end_date}",
        metrics=metrics,
        evaluated_intervals=metrics.matched_intervals,
        status="ok" if metrics.matched_intervals else "insufficient_data",
    )
