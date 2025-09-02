from __future__ import annotations

import json
import logging
import time
import uuid
from typing import Callable

from django.http import HttpRequest, HttpResponse

logger = logging.getLogger(__name__)


class RequestLogMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        req_id = request.headers.get('X-Request-ID') or str(uuid.uuid4())
        request.META['HTTP_X_REQUEST_ID'] = req_id
        start = time.time()
        response = self.get_response(request)
        duration_ms = int((time.time() - start) * 1000)
        try:
            user = getattr(request, 'user', None)
            payload = {
                'event': 'http_request',
                'id': req_id,
                'method': request.method,
                'path': request.path,
                'status': response.status_code,
                'ms': duration_ms,
                'user': getattr(user, 'username', None) if user and user.is_authenticated else None,
            }
            logger.info(json.dumps(payload))
        except Exception:
            pass
        response['X-Request-ID'] = req_id
        return response

