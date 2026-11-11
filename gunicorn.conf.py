# Gunicorn loads this file automatically from the working directory.
from gunicorn.glogging import Logger

HEALTH_CHECK_PATHS = {"/healthz"}


class QuietHealthCheckLogger(Logger):
    """Access log without the host's health checks (Render pings every few seconds)."""

    def access(self, resp, req, environ, request_time):
        if req.path in HEALTH_CHECK_PATHS:
            return
        super().access(resp, req, environ, request_time)


logger_class = QuietHealthCheckLogger
