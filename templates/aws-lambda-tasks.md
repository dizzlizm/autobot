# AWS Lambda API Backend
Build a serverless API with Python Lambda functions.

## Task 1: Create project structure
Create these files:
- `requirements.txt` with: boto3, requests
- `template.yaml` (SAM template) with basic Globals for Python 3.11 runtime
- `src/` directory for lambda handlers
- `.gitignore` with: `__pycache__/`, `.aws-sam/`, `*.pyc`, `.env`

## Task 2: Create hello world lambda
Create `src/hello/handler.py` with:
- A function `handler(event, context)`
- Returns JSON response with statusCode 200
- Body contains: `{"message": "Hello from Lambda", "path": event.get("path")}`
- Add proper CORS headers: `Access-Control-Allow-Origin: *`

## Task 3: Create user GET lambda
Create `src/users/get_user.py` with:
- Function `handler(event, context)`
- Extract `user_id` from `event["pathParameters"]["id"]`
- Return mock user data: `{"id": user_id, "name": "Test User", "email": "test@example.com"}`
- Return 404 if no user_id provided
- Include CORS headers

## Task 4: Create user POST lambda
Create `src/users/create_user.py` with:
- Function `handler(event, context)`
- Parse JSON body with `json.loads(event.get("body", "{}"))`
- Validate required fields: name, email
- Return 400 with error message if validation fails
- Return 201 with created user data on success
- Include CORS headers

## Task 5: Create DynamoDB helper
Create `src/utils/dynamodb.py` with:
- Import boto3
- Function `get_table(table_name)` returns dynamodb Table resource
- Function `get_item(table, key)` returns item or None
- Function `put_item(table, item)` saves item and returns it
- Use `os.environ.get("TABLE_NAME", "users")` for table name

## Task 6: Create response helper
Create `src/utils/response.py` with:
- Function `success(body, status=200)` returns properly formatted API Gateway response
- Function `error(message, status=400)` returns error response
- Both include CORS headers
- Both json.dumps the body

## Task 7: Create list users lambda
Create `src/users/list_users.py` with:
- Function `handler(event, context)`
- Use the dynamodb helper to scan the table
- Support optional query param `limit` (default 10)
- Return array of users with count
- Handle errors gracefully

## Task 8: Create delete user lambda
Create `src/users/delete_user.py` with:
- Function `handler(event, context)`
- Extract user_id from path parameters
- Delete from DynamoDB
- Return 204 on success, 404 if not found
- Use response helper for consistency

## Task 9: Update SAM template
Update `template.yaml` with:
- All lambda functions defined as AWS::Serverless::Function
- API Gateway events for each endpoint
- Environment variable for TABLE_NAME
- DynamoDB table resource with id as partition key
- Proper IAM policies for DynamoDB access

## Task 10: Create local test script
Create `test_local.py` with:
- Import each handler
- Create mock events for each endpoint
- Call handlers and print responses
- Test happy path and error cases
