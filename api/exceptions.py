"""Custom DRF exception handler — consistent error shape across all endpoints."""
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        errors = response.data
        if isinstance(errors, dict):
            detail = errors.get('detail', errors)
        elif isinstance(errors, list):
            detail = errors
        else:
            detail = str(errors)

        response.data = {
            'error': True,
            'status_code': response.status_code,
            'detail': detail,
        }

    return response
