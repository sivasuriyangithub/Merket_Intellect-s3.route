import logging
import sys
from datetime import datetime

from pythonjsonlogger import jsonlogger


def get_client_ip(request):
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0]
    else:
        ip = request.META.get("REMOTE_ADDR")
    return ip


class HTTPRequestLogRecord(object):
    def __init__(self, record: logging.LogRecord):
        self.requestMethod = record.request.method
        self.requestUrl = record.request.path
        self.status = record.status_code
        self.remoteIp = get_client_ip(record.request)
        self.latency = record.msecs
        self.protocol = record.request.scheme
        self.message = record.msg

    def msg(self):
        latency = str(self.latency)
        if not latency.endswith("ms"):
            latency = latency[:3] + "ms"
        return {
            "message": self.message,
            "httpRequest": {
                "requestMethod": self.requestMethod,
                "requestUrl": self.requestUrl,
                "status": self.status,
                "remoteIp": self.remoteIp,
                "latency": latency,
                "protocol": str(self.protocol).upper() + "/1.1",
            },
        }


class DjangoJsonFormatter(jsonlogger.JsonFormatter):
    """Extend the json formatter to include more fields.
    Note:
    It is possible to get a similar outcome by supplying a
    format string with the desired parameters when initializing
    the JsonFormatter, but that relies on regex, and the mapping
    key ends up being the same. Here, we can have funcName->function,
    where 'function' is a semantic improvement.
    See http://bit.ly/1OaJylG
    """

    def add_fields(self, log_record, record, message_dict):
        """Supply additional data to dict for logging."""
        super(DjangoJsonFormatter, self).add_fields(log_record, record, message_dict)
        if request := log_record.pop("request", None):
            log_record["httpRequest"] = HTTPRequestLogRecord(record).msg()[
                "httpRequest"
            ]
            try:
                log_record["user_id"] = request.user.pk
            except (AttributeError, KeyError):
                pass
            request_id = request.headers.get("X-Request-Id")
            request_producer = request.headers.get("X-Request-Producer", None)
            if request_id:
                log_record["operation"] = {"id": request_id}
                if request_producer:
                    log_record["operation"]["producer"] = request_producer
        log_record["log"] = record.name
        log_record["severity"] = record.levelname
        log_record["function"] = record.funcName
        log_record["line"] = record.lineno
        log_record["file"] = record.filename
        log_record["module"] = record.module
        log_record["time"] = datetime.fromtimestamp(record.created)


def setup_json_logging_to_stdout(level):
    jsonformatter = JsonFormatter(datefmt="%Y-%m-%dT%H:%M:%SZ")
    streamhandler = logging.StreamHandler(stream=sys.stdout)
    streamhandler.setLevel(level)
    streamhandler.setFormatter(jsonformatter)

    root_logger = logging.getLogger()
    root_logger.addHandler(streamhandler)

    root_ll = root_logger.getEffectiveLevel()
    if level < root_ll or root_ll == logging.NOTSET:
        root_logger.setLevel(level)
