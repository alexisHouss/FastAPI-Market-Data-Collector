import redis
import os

# Create a Redis connection
r = redis.Redis(
    host=os.getenv("REDIS_CACHE_HOST", "redis"),
    port=os.getenv("REDIS_CACHE_PORT", 6379),
    db=os.getenv("REDIS_CACHE_DB", 1),
)


def set(key, value, cache_time=None):
    """
    Set a key-value pair in the Redis cache with an optional expiry time.

    :param key: The key to be set.
    :param value: The value to be stored.
    :param cache_time: Expiration time in seconds. If None, the key will not expire.
    """
    return r.set(key, value, ex=cache_time)


def get(key, default_to_return=None):
    """
    Get the value for a given key from the Redis cache.

    :param key: The key to retrieve.
    :return: The value associated with the key or None if the key doesn't exist.
    """
    return r.get(key) or default_to_return
