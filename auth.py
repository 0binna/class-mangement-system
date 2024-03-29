import os
import json
from flask import request, _request_ctx_stack
from functools import wraps
from jose import jwt
from urllib.request import urlopen
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

AUTH0_DOMAIN = os.getenv('AUTH0_DOMAIN')
ALGORITHMS = os.getenv('ALGORITHMS')
API_AUDIENCE = os.getenv('API_AUDIENCE')


class AuthError(Exception):
    '''
    AuthError Exception
    A standardized way to communicate auth failure modes
    '''

    def __init__(self, error, status_code):
        self.error = error
        self.status_code = status_code


def get_token_auth_header():
    # Auth header
    # Obtains the Access Token from the Authorization Header
    auth = request.headers.get('Authorization', None)
    # Attempts to get the header from the request. Raises an AuthError if no
    # header is present
    if not auth:
        raise AuthError({
            'error': 401,
            'code': 'authorization_header_missing',
            'description': 'Authorization header is expected.'
        }, 401)

    # Attempts to split bearer and the token. Raises an AuthError if the
    # header is malformed
    parts = auth.split()
    if parts[0].lower() != 'bearer':
        raise AuthError({
            'error': 401,
            'code': 'invalid_header',
            'description': 'Authorization header must start with "Bearer".'
        }, 401)

    elif len(parts) == 1:
        raise AuthError({
            'error': 401,
            'code': 'invalid_header',
            'description': 'Token not found.'
        }, 401)

    elif len(parts) > 2:
        raise AuthError({
            'error': 401,
            'code': 'invalid_header',
            'description': 'Authorization header must be bearer token.'
        }, 401)

    token = parts[1]
    return token


def check_permissions(permission, payload):
    '''
    check_permissions(permission, payload) method
        @INPUTS
                permission: string permission (i.e. 'get:students')
                payload: decoded jwt payload
    '''
    # Raises an AuthError if permissions are not included in the payload
    if 'permissions' not in payload:
        raise AuthError({
            'error': 400,
            'code': 'invalid_claims',
            'description': 'Permissions not included in JWT.'
        }, 400)

    if permission not in payload['permissions']:
        # Raises an AuthError if the requested permission string is not in the
        # payload permissions array returns true otherwise
        raise AuthError({
            'error': 403,
            'code': 'unauthorized',
            'description': 'Permission not found.'
        }, 403)
    return True


def verify_decode_jwt(token):
    '''
    verify_decode_jwt(token) method
        @INPUTS
                token: a json web token (string)
    '''
    # Verifies the token using Auth0 /.well-known/jwks.json
    jsonurl = urlopen(f'https://{AUTH0_DOMAIN}/.well-known/jwks.json')
    jwks = json.loads(jsonurl.read())
    unverified_header = jwt.get_unverified_header(token)
    rsa_key = {}
    if 'kid' not in unverified_header:
        raise AuthError({
            'error': 401,
            'code': 'invalid_header',
            'description': 'Authorization malformed.'
        }, 401)

    for key in jwks['keys']:
        if key['kid'] == unverified_header['kid']:
            rsa_key = {
                'kty': key['kty'],
                'kid': key['kid'],
                'use': key['use'],
                'n': key['n'],
                'e': key['e']
            }

    # Decodes the payload from the token, validates the claims and returns the
    # decoded payload
    if rsa_key:
        try:
            payload = jwt.decode(
                token,
                rsa_key,
                algorithms=ALGORITHMS,
                audience=API_AUDIENCE,
                issuer='https://' + AUTH0_DOMAIN + '/'
            )

            return payload

        except jwt.ExpiredSignatureError:
            raise AuthError({
                'error': 401,
                'code': 'token_expired',
                'description': 'Token expired.'
            }, 401)

        except jwt.JWTClaimsError:
            raise AuthError({
                'error': 401,
                'code': 'invalid_claims',
                'description': 'Incorrect claims. '
                + 'Please, check the audience and issuer.'
            }, 401)
        except Exception:
            raise AuthError({
                'error': 400,
                'code': 'invalid_header',
                'description': 'Unable to parse authentication token.'
            }, 400)
    raise AuthError({
        'error': 400,
        'code': 'invalid_header',
                'description': 'Unable to find the appropriate key.'
    }, 400)


def requires_auth(permission=''):
    '''
    @requires_auth(permission) decorator method
        @INPUTS
                permission: string permission (i.e. 'get:students')
    '''
    def requires_auth_decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            token = get_token_auth_header()
            payload = verify_decode_jwt(token)
            check_permissions(permission, payload)
            return f(token, *args, **kwargs)

        return wrapper
    return requires_auth_decorator
