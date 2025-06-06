import json
import os
from flask import abort, request
from functools import wraps
from jose import jwt
from urllib.request import urlopen
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Access the environment variables
AUTH0_DOMAIN = os.getenv("AUTH0_DOMAIN")
ALGORITHMS = [os.getenv("ALGORITHMS")]
API_AUDIENCE = os.getenv("API_AUDIENCE")

## AuthError Exception
"""
AuthError Exception
A standardized way to communicate auth failure modes
"""


class AuthError(Exception):
    def __init__(self, error, status_code):
        self.error = error
        self.status_code = status_code


## Auth Header


"""
implement get_token_auth_header() method
    it should attempt to get the header from the request
        it should raise an AuthError if no header is present
    it should attempt to split bearer and the token
        it should raise an AuthError if the header is malformed
    return the token part of the header
"""


def get_token_auth_header():
    # Partially taken from lesson 2.15 Practice - Applying Skills in Flask from the course
    if "Authorization" not in request.headers:
        # We do not include descriptive error information for security's sake
        raise AuthError({"code": "unauthorized", "description": "Unauthorized"}, 401)
    auth_header = request.headers["Authorization"]
    pieces = auth_header.split(" ")
    if len(pieces) != 2:
        # We do not include descriptive error information for security's sake
        raise AuthError({"code": "unauthorized", "description": "Unauthorized"}, 401)
    elif pieces[0].lower() != "bearer":
        # We do not include descriptive error information for security's sake
        raise AuthError({"code": "unauthorized", "description": "Unauthorized"}, 401)
    return pieces[1]


"""
implement check_permissions(permission, payload) method
    @INPUTS
        permission: string permission (i.e. 'post:drink')
        payload: decoded jwt payload

    it should raise an AuthError if permissions are not included in the payload
        !!NOTE check your RBAC settings in Auth0
    it should raise an AuthError if the requested permission string is not in the payload permissions array
    return true otherwise
"""


def check_permissions(permission, payload):
    if "permissions" not in payload:
        # We do not include descriptive error information for security's sake
        raise AuthError({"code": "forbidden", "description": "Forbidden"}, 403)
    if permission not in payload["permissions"]:
        # We do not include descriptive error information for security's sake
        raise AuthError({"code": "forbidden", "description": "Forbidden"}, 403)
    return True


"""
implement verify_decode_jwt(token) method
    @INPUTS
        token: a json web token (string)

    it should be an Auth0 token with key id (kid)
    it should verify the token using Auth0 /.well-known/jwks.json
    it should decode the payload from the token
    it should validate the claims
    return the decoded payload

    !!NOTE urlopen has a common certificate error described here: https://stackoverflow.com/questions/50236117/scraping-ssl-certificate-verify-failed-error-for-http-en-wikipedia-org
"""


def verify_decode_jwt(token):
    # Taken from the 2.10 Practice - Validating Auth0 Tokens exercise in the course
    jsonurl = urlopen(f"https://{AUTH0_DOMAIN}/.well-known/jwks.json")
    jwks = json.loads(jsonurl.read())

    unverified_header = jwt.get_unverified_header(token)

    rsa_key = {}
    if "kid" not in unverified_header:
        raise AuthError(
            {"code": "invalid_header", "description": "Authorization malformed."}, 401
        )

    for key in jwks["keys"]:
        if key["kid"] == unverified_header["kid"]:
            rsa_key = {
                "kty": key["kty"],
                "kid": key["kid"],
                "use": key["use"],
                "n": key["n"],
                "e": key["e"],
            }

    if rsa_key:
        try:
            payload = jwt.decode(
                token,
                rsa_key,
                algorithms=ALGORITHMS,
                audience=API_AUDIENCE,
                issuer="https://" + AUTH0_DOMAIN + "/",
            )

            return payload

        except jwt.ExpiredSignatureError:
            raise AuthError(
                {"code": "token_expired", "description": "Token expired."}, 401
            )

        except jwt.JWTClaimsError:
            raise AuthError(
                {
                    "code": "invalid_claims",
                    "description": "Incorrect claims. Please, check the audience and issuer.",
                },
                403,
            )
        except Exception:
            raise AuthError(
                {
                    "code": "invalid_header",
                    "description": "Unable to parse authentication token.",
                },
                403,
            )
    raise AuthError(
        {
            "code": "invalid_header",
            "description": "Unable to find the appropriate key.",
        },
        403,
    )


"""
implement @requires_auth(permission) decorator method
    @INPUTS
        permission: string permission (i.e. 'post:drink')

    it should use the get_token_auth_header method to get the token
    it should use the verify_decode_jwt method to decode the jwt
    it should use the check_permissions method validate claims and check the requested permission
    return the decorator which passes the decoded payload to the decorated method
"""


def requires_auth(permission=""):
    def requires_auth_decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            try:
                token = get_token_auth_header()
                payload = verify_decode_jwt(token)
                check_permissions(permission, payload)
                return f(*args, **kwargs)
            except AuthError as e:
                abort(e.status_code, e)

        return wrapper

    return requires_auth_decorator
