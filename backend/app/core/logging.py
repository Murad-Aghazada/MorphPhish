import json, logging, sys
from datetime import datetime, timezone
class JsonFormatter(logging.Formatter):
    def format(self, record):
        payload={"ts":datetime.now(timezone.utc).isoformat(),"level":record.levelname,"logger":record.name,"message":record.getMessage()}
        if record.exc_info: payload["exception"]=self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)
def configure_logging(level="INFO"):
    h=logging.StreamHandler(sys.stdout); h.setFormatter(JsonFormatter())
    root=logging.getLogger(); root.handlers=[h]; root.setLevel(level)
