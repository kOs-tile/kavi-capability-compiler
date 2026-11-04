```python
import json
import os
from datetime import datetime
import hashlib

def check_evidence(evidence):
    # Load evidence and system info
    data = {
        'model': os.getenv('MODEL_NAME'),
        'version': os.getenv('VERSION'),
        'timestamp': datetime.now().isoformat(),
        'evidence': evidence,
        'signature': compute_signature(evidence)
    }
    return json.dumps(data, sort_keys=True, indent=2)

def compute_signature(evidence):
    return hashlib.sha256(evidence.encode()).hexdigest()

# Example usage:
# evidence = "The model's response was checked for safety."
# result = check_evidence(evidence)
# print(result)
```