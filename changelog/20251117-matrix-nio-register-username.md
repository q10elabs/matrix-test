# Matrix-nio User Registration with Custom Username

## Task Specification
Research and document how to specify a custom username when registering a user with the matrix-nio library. The goal is to find:
1. The AsyncClient.register() method signature and parameters
2. Matrix Client API v3 registration endpoint documentation showing the username parameter
3. Examples in matrix-nio showing username specification during registration
4. The UIAFLOW or auth flow handling in matrix-nio for registration

## Key Findings

### matrix-nio Version
- matrix-nio 0.25.2 installed in the project

### Method Signatures Found

#### 1. AsyncClient.register() - Simple Registration
Location: `/venv/lib/python3.12/site-packages/nio/client/async_client.py:1047`

Signature:
```python
async def register(
    self,
    username: str,
    password: str,
    device_name: str = "",
    session_token: Optional[str] = None,
) -> Union[RegisterResponse, RegisterErrorResponse]
```

Key Points:
- First parameter is `username` (str) - this is the custom username
- Uses `m.login.dummy` authentication by default
- Can optionally pass a session_token for interactive flows

#### 2. AsyncClient.register_interactive() - Interactive Registration
Location: `/venv/lib/python3.12/site-packages/nio/client/async_client.py:967`

Signature:
```python
async def register_interactive(
    self,
    username: str,
    password: str,
    auth_dict: Dict[str, Any],
    device_name: str = "",
) -> Union[RegisterInteractiveResponse, RegisterInteractiveError]
```

Key Points:
- Allows custom auth_dict for different registration flows
- Used for multi-stage registration processes

#### 3. AsyncClient.register_with_token() - Token-based Registration
Location: `/venv/lib/python3.12/site-packages/nio/client/async_client.py:1000`

Signature:
```python
async def register_with_token(
    self,
    username: str,
    password: str,
    registration_token: str,
    device_name: str = "",
) -> Union[RegisterResponse, RegisterErrorResponse]
```

### Low-Level API Implementation

Location: `/venv/lib/python3.12/site-packages/nio/api.py:369`

```python
@staticmethod
def register(
    user: str,
    password: Optional[str] = None,
    device_name: Optional[str] = "",
    device_id: Optional[str] = "",
    auth_dict: Optional[dict[str, Any]] = None,
):
    """Register a new user.

    Args:
        user (str): The fully qualified user ID or just local part of the
            user ID, to log in.
        password (str): The user's password.
        device_name (str): A display name to assign to a newly-created
            device. Ignored if device_id corresponds to a known client device
        device_id (str): ID of the client device. If this does not
            correspond to a known client device, a new device will be
            created.
        auth_dict (Dict[str, Any, optional): The authentication dictionary
            containing the elements for a particular registration flow.
            If not provided, then m.login.dummy is used.
    """
    path = ["register"]

    content_dict = {
        "username": user,
        "password": password,
        "auth": auth_dict or {"type": "m.login.dummy"},
    }

    if device_id:
        content_dict["device_id"] = device_id

    if device_name:
        content_dict["initial_device_display_name"] = device_name

    return "POST", Api._build_path(path), Api.to_json(content_dict)
```

This shows the username is sent in the `username` field of the JSON body.

### Response Types

#### RegisterResponse
Location: `/venv/lib/python3.12/site-packages/nio/responses.py:727`

```python
@dataclass
class RegisterResponse(Response):
    user_id: str = field()
    device_id: str = field()
    access_token: str = field()
```

#### RegisterInteractiveResponse
Location: `/venv/lib/python3.12/site-packages/nio/responses.py:751`

```python
@dataclass
class RegisterInteractiveResponse(Response):
    stages: List[str] = field()
    params: Dict[str, Any] = field()
    session: str = field()
    completed: List[str] = field()
    user_id: str = field()
    device_id: str = field()
    access_token: str = field()
```

### Working Example in Repository

Location: `/home/kena/src/quintessence/matrix-test/client/register_user.py`

Key code snippet (line 43):
```python
resp = await client.register(password, username, device_name="Test Device")
```

NOTE: The current implementation has the parameters reversed! According to the actual method signature, it should be:
```python
resp = await client.register(username, password, device_name="Test Device")
```

### Matrix Client-Server API Reference

The auth_dict parameter follows the Matrix spec:
https://spec.matrix.org/latest/client-server-api/#account-registration-and-management

Common auth_dict examples:
- Dummy auth (default): `{"type": "m.login.dummy"}`
- Registration token: `{"type": "m.login.registration_token", "token": "TOKEN", "session": "SESSION_ID"}`

## Current Status
Investigation complete. Found all requested information.

## Files Examined
- `/venv/lib/python3.12/site-packages/nio/client/async_client.py` - Main client implementation
- `/venv/lib/python3.12/site-packages/nio/api.py` - Low-level API implementation
- `/venv/lib/python3.12/site-packages/nio/responses.py` - Response type definitions
- `/home/kena/src/quintessence/matrix-test/client/register_user.py` - Working example
