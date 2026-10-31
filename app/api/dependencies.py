from fastapi import Request

from app.services.data_service import DataService


def get_data_service(request: Request) -> DataService:
    return request.app.state.data_service
