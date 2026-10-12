import logging
import json
import traceback
from datetime import datetime
from contextvars import ContextVar

correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")

class JSONFormatter(logging.Formatter):
    """
    Formatter that outputs JSON strings after parsing the LogRecord.
    """
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "event": record.getMessage(),
            "name": record.name,
        }

        # Try to pull correlation_id from ContextVar if available
        cid = correlation_id_var.get()
        if cid:
            log_data["correlation_id"] = cid
            
        if hasattr(record, "correlation_id"):
            log_data["correlation_id"] = record.correlation_id

        if hasattr(record, "request_path"):
            log_data["request_path"] = record.request_path
            
        if hasattr(record, "request_method"):
            log_data["request_method"] = record.request_method
            
        if hasattr(record, "provider_name"):
            log_data["provider_name"] = record.provider_name
            
        if hasattr(record, "retrieval_duration_ms"):
            log_data["retrieval_duration_ms"] = record.retrieval_duration_ms
            
        if hasattr(record, "result_count"):
            log_data["result_count"] = record.result_count
            
        if hasattr(record, "provider_latency_ms"):
            log_data["provider_latency_ms"] = record.provider_latency_ms
            
        if hasattr(record, "error_category"):
            log_data["error_category"] = record.error_category

        if record.exc_info:
            log_data["exception"] = "".join(traceback.format_exception(*record.exc_info))

        return json.dumps(log_data)

def setup_logging():
    handler = logging.StreamHandler()
    formatter = JSONFormatter()
    handler.setFormatter(formatter)
    
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Remove existing handlers to avoid duplicate logs
    for h in root_logger.handlers[:]:
        root_logger.removeHandler(h)
        
    root_logger.addHandler(handler)

    # Uvicorn logs override
    logging.getLogger("uvicorn.access").handlers = [handler]
    logging.getLogger("uvicorn.error").handlers = [handler]
