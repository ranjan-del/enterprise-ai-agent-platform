"""Redis client factory (session memory + rate limiting + pub/sub).

TODO: checklist "Backend: ... Redis" and "Memory subsystems: session".
"""
# import redis.asyncio as redis

from app.core.config import settings

# TODO: pool = redis.ConnectionPool.from_url(settings.redis_url)


def get_redis():
    """Return a Redis client bound to the shared connection pool."""
    # TODO: return redis.Redis(connection_pool=pool)
    raise NotImplementedError("get_redis not implemented")


_ = settings  # referenced so config import is exercised
