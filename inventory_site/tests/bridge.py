"""Line-based native Python bridge for DOM component integration tests only."""
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"dist/assets/python"))
import lab_api
import stress_api

print(json.dumps({"type":"ready"}),flush=True)
for line in sys.stdin:
    message=json.loads(line)
    try:
        payload=message["payload"]
        handler=stress_api if payload.get("op","").startswith("stress_") else lab_api
        result=json.loads(handler.handle_json(json.dumps(payload)))
        response={"type":"result","id":message["id"],"result":result}
    except Exception as error:
        response={"type":"error","id":message["id"],"message":str(error)}
    print(json.dumps(response,default=lab_api.scalar,allow_nan=False),flush=True)
