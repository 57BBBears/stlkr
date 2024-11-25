from itsdangerous import URLSafeTimedSerializer


def get_url_serializer(secret_key: str) -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(secret_key)
