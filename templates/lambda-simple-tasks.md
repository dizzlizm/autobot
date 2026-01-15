# Simple Lambda Function
One small Lambda for small models (1.5b).

## Task 1: Create handler file
Create `handler.py` with:
```python
import json

def handler(event, context):
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"message": "Hello"})
    }
```

## Task 2: Add request parsing
Update `handler.py` to:
- Get HTTP method from `event.get("httpMethod")`
- Get path from `event.get("path")`
- Get query params from `event.get("queryStringParameters") or {}`
- Include these in the response body

## Task 3: Add body parsing
Update `handler.py` to:
- Parse body with `json.loads(event.get("body") or "{}")`
- Handle JSONDecodeError and return 400
- Echo the parsed body in response

## Task 4: Add name parameter
Update `handler.py` to:
- Get "name" from query params or body
- If name exists, return `{"message": f"Hello, {name}!"}`
- If no name, return `{"message": "Hello, stranger!"}`

## Task 5: Add requirements
Create `requirements.txt` with just:
```
boto3
```

## Task 6: Add error handling
Update `handler.py` to:
- Wrap main logic in try/except
- Return 500 with error message on exception
- Log error with print()
