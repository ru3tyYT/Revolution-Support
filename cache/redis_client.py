"""Redis client wrapper for Discord support bot.

Provides connection pooling, rate limiting, caching decorators,
and session management with proper type hints and error handling.
"""

import asyncio
import functools
import hashlib
import json
import logging
from contextlib import asynccontextmanager
from typing import (
    Any,
    AsyncGenerator,
    Callable,
    Dict,
    List,
    Optional,
    TypeVar,
    Union,
)

import redis.asyncio as aioredis
from redis.asyncio import Redis

from ..monitoring.metrics import (
    track_redis_connection,
    track_redis_operation,
    track_redis_operation_duration,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")
F = TypeVar("F", bound=Callable[..., Any])


class RedisClient:
    """Redis client wrapper with connection pooling."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        pool_size: int = 10,
        socket_timeout: float = 5.0,
        socket_connect_timeout: float = 5.0,
        health_check_interval: float = 30.0,
        decode_responses: bool = True,
    ):
        """Initialize Redis client.

        Args:
            host: Redis server host.
            port: Redis server port.
            db: Redis database number.
            password: Redis password.
            pool_size: Connection pool size.
            socket_timeout: Socket timeout in seconds.
            socket_connect_timeout: Connection timeout in seconds.
            health_check_interval: Health check interval in seconds.
            decode_responses: Whether to decode responses as strings.
        """
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.pool_size = pool_size
        self.socket_timeout = socket_timeout
        self.socket_connect_timeout = socket_connect_timeout
        self.health_check_interval = health_check_interval
        self.decode_responses = decode_responses

        self._pool: Optional[Redis] = None
        self._lock = asyncio.Lock()
        self._closed = True

    async def connect(self) -> None:
        """Establish connection to Redis."""
        if self._pool is not None:
            return

        async with self._lock:
            if self._pool is not None:
                return

            try:
                self._pool = await aioredis.from_url(
                    f"redis://{self.host}:{self.port}/{self.db}",
                    password=self.password,
                    max_connections=self.pool_size,
                    socket_timeout=self.socket_timeout,
                    socket_connect_timeout=self.socket_connect_timeout,
                    health_check_interval=self.health_check_interval,
                    decode_responses=self.decode_responses,
                )
                self._closed = False
                track_redis_connection("main", self.pool_size)
                logger.info(
                    "Redis connection established",
                    extra={"host": self.host, "port": self.port, "db": self.db},
                )
            except Exception as e:
                logger.error(
                    "Failed to connect to Redis",
                    extra={"error": str(e), "host": self.host, "port": self.port},
                )
                raise

    async def close(self) -> None:
        """Close Redis connection."""
        if self._pool is None or self._closed:
            return

        async with self._lock:
            if self._pool is None or self._closed:
                return

            await self._pool.close()
            self._closed = True
            track_redis_connection("main", 0)
            logger.info("Redis connection closed")

    async def ping(self) -> bool:
        """Check Redis connection health.

        Returns:
            True if connection is healthy.
        """
        if self._pool is None:
            return False

        try:
            with track_redis_operation_duration("PING"):
                result = await self._pool.ping()
            track_redis_operation("PING", "success")
            return result
        except Exception as e:
            track_redis_operation("PING", "error")
            logger.error("Redis ping failed", extra={"error": str(e)})
            return False

    async def get(self, key: str) -> Optional[str]:
        """Get value by key.

        Args:
            key: Redis key.

        Returns:
            Value or None if not found.
        """
        await self.connect()

        try:
            with track_redis_operation_duration("GET"):
                value = await self._pool.get(key)
            track_redis_operation("GET", "success")
            return value
        except Exception as e:
            track_redis_operation("GET", "error")
            logger.error("Redis GET failed", extra={"key": key, "error": str(e)})
            raise

    async def set(
        self,
        key: str,
        value: Union[str, bytes, int, float],
        expire: Optional[int] = None,
        nx: bool = False,
        xx: bool = False,
    ) -> bool:
        """Set key-value pair.

        Args:
            key: Redis key.
            value: Value to store.
            expire: Expiration time in seconds.
            nx: Only set if key does not exist.
            xx: Only set if key exists.

        Returns:
            True if set was successful.
        """
        await self.connect()

        try:
            with track_redis_operation_duration("SET"):
                result = await self._pool.set(key, value, ex=expire, nx=nx, xx=xx)
            track_redis_operation("SET", "success")
            return result
        except Exception as e:
            track_redis_operation("SET", "error")
            logger.error(
                "Redis SET failed",
                extra={"key": key, "error": str(e)},
            )
            raise

    async def delete(self, *keys: str) -> int:
        """Delete keys.

        Args:
            *keys: Keys to delete.

        Returns:
            Number of keys deleted.
        """
        await self.connect()

        try:
            with track_redis_operation_duration("DELETE"):
                result = await self._pool.delete(*keys)
            track_redis_operation("DELETE", "success")
            return result
        except Exception as e:
            track_redis_operation("DELETE", "error")
            logger.error("Redis DELETE failed", extra={"keys": keys, "error": str(e)})
            raise

    async def exists(self, *keys: str) -> int:
        """Check if keys exist.

        Args:
            *keys: Keys to check.

        Returns:
            Number of keys that exist.
        """
        await self.connect()

        try:
            with track_redis_operation_duration("EXISTS"):
                result = await self._pool.exists(*keys)
            track_redis_operation("EXISTS", "success")
            return result
        except Exception as e:
            track_redis_operation("EXISTS", "error")
            logger.error("Redis EXISTS failed", extra={"keys": keys, "error": str(e)})
            raise

    async def expire(self, key: str, seconds: int) -> bool:
        """Set key expiration.

        Args:
            key: Redis key.
            seconds: Expiration time in seconds.

        Returns:
            True if expiration was set.
        """
        await self.connect()

        try:
            with track_redis_operation_duration("EXPIRE"):
                result = await self._pool.expire(key, seconds)
            track_redis_operation("EXPIRE", "success")
            return result
        except Exception as e:
            track_redis_operation("EXPIRE", "error")
            logger.error(
                "Redis EXPIRE failed",
                extra={"key": key, "error": str(e)},
            )
            raise

    async def ttl(self, key: str) -> int:
        """Get time to live for a key.

        Args:
            key: Redis key.

        Returns:
            TTL in seconds, -1 if no expiration, -2 if key doesn't exist.
        """
        await self.connect()

        try:
            with track_redis_operation_duration("TTL"):
                result = await self._pool.ttl(key)
            track_redis_operation("TTL", "success")
            return result
        except Exception as e:
            track_redis_operation("TTL", "error")
            logger.error("Redis TTL failed", extra={"key": key, "error": str(e)})
            raise

    async def incr(self, key: str, amount: int = 1) -> int:
        """Increment key value.

        Args:
            key: Redis key.
            amount: Amount to increment by.

        Returns:
            New value.
        """
        await self.connect()

        try:
            with track_redis_operation_duration("INCR"):
                result = await self._pool.incrby(key, amount)
            track_redis_operation("INCR", "success")
            return result
        except Exception as e:
            track_redis_operation("INCR", "error")
            logger.error("Redis INCR failed", extra={"key": key, "error": str(e)})
            raise

    async def decr(self, key: str, amount: int = 1) -> int:
        """Decrement key value.

        Args:
            key: Redis key.
            amount: Amount to decrement by.

        Returns:
            New value.
        """
        await self.connect()

        try:
            with track_redis_operation_duration("DECR"):
                result = await self._pool.decrby(key, amount)
            track_redis_operation("DECR", "success")
            return result
        except Exception as e:
            track_redis_operation("DECR", "error")
            logger.error("Redis DECR failed", extra={"key": key, "error": str(e)})
            raise

    async def hget(self, name: str, key: str) -> Optional[str]:
        """Get hash field value.

        Args:
            name: Hash name.
            key: Field key.

        Returns:
            Field value or None.
        """
        await self.connect()

        try:
            with track_redis_operation_duration("HGET"):
                result = await self._pool.hget(name, key)
            track_redis_operation("HGET", "success")
            return result
        except Exception as e:
            track_redis_operation("HGET", "error")
            logger.error(
                "Redis HGET failed",
                extra={"name": name, "key": key, "error": str(e)},
            )
            raise

    async def hset(
        self,
        name: str,
        key: Optional[str] = None,
        value: Optional[str] = None,
        mapping: Optional[Dict[str, str]] = None,
    ) -> int:
        """Set hash field(s).

        Args:
            name: Hash name.
            key: Field key (if setting single field).
            value: Field value (if setting single field).
            mapping: Dictionary of fields to set.

        Returns:
            Number of fields added.
        """
        await self.connect()

        try:
            with track_redis_operation_duration("HSET"):
                result = await self._pool.hset(name, key, value, mapping=mapping)
            track_redis_operation("HSET", "success")
            return result
        except Exception as e:
            track_redis_operation("HSET", "error")
            logger.error(
                "Redis HSET failed",
                extra={"name": name, "error": str(e)},
            )
            raise

    async def hgetall(self, name: str) -> Dict[str, str]:
        """Get all hash fields.

        Args:
            name: Hash name.

        Returns:
            Dictionary of all fields.
        """
        await self.connect()

        try:
            with track_redis_operation_duration("HGETALL"):
                result = await self._pool.hgetall(name)
            track_redis_operation("HGETALL", "success")
            return result
        except Exception as e:
            track_redis_operation("HGETALL", "error")
            logger.error(
                "Redis HGETALL failed",
                extra={"name": name, "error": str(e)},
            )
            raise

    async def lpush(self, name: str, *values: str) -> int:
        """Push values to the left of a list.

        Args:
            name: List name.
            *values: Values to push.

        Returns:
            Length of list after push.
        """
        await self.connect()

        try:
            with track_redis_operation_duration("LPUSH"):
                result = await self._pool.lpush(name, *values)
            track_redis_operation("LPUSH", "success")
            return result
        except Exception as e:
            track_redis_operation("LPUSH", "error")
            logger.error(
                "Redis LPUSH failed",
                extra={"name": name, "error": str(e)},
            )
            raise

    async def rpop(self, name: str) -> Optional[str]:
        """Pop value from the right of a list.

        Args:
            name: List name.

        Returns:
            Popped value or None.
        """
        await self.connect()

        try:
            with track_redis_operation_duration("RPOP"):
                result = await self._pool.rpop(name)
            track_redis_operation("RPOP", "success")
            return result
        except Exception as e:
            track_redis_operation("RPOP", "error")
            logger.error(
                "Redis RPOP failed",
                extra={"name": name, "error": str(e)},
            )
            raise

    async def lrange(self, name: str, start: int, end: int) -> List[str]:
        """Get range of values from a list.

        Args:
            name: List name.
            start: Start index.
            end: End index.

        Returns:
            List of values.
        """
        await self.connect()

        try:
            with track_redis_operation_duration("LRANGE"):
                result = await self._pool.lrange(name, start, end)
            track_redis_operation("LRANGE", "success")
            return result
        except Exception as e:
            track_redis_operation("LRANGE", "error")
            logger.error(
                "Redis LRANGE failed",
                extra={"name": name, "error": str(e)},
            )
            raise

    async def sadd(self, name: str, *values: str) -> int:
        """Add values to a set.

        Args:
            name: Set name.
            *values: Values to add.

        Returns:
            Number of values added.
        """
        await self.connect()

        try:
            with track_redis_operation_duration("SADD"):
                result = await self._pool.sadd(name, *values)
            track_redis_operation("SADD", "success")
            return result
        except Exception as e:
            track_redis_operation("SADD", "error")
            logger.error(
                "Redis SADD failed",
                extra={"name": name, "error": str(e)},
            )
            raise

    async def smembers(self, name: str) -> set:
        """Get all members of a set.

        Args:
            name: Set name.

        Returns:
            Set of members.
        """
        await self.connect()

        try:
            with track_redis_operation_duration("SMEMBERS"):
                result = await self._pool.smembers(name)
            track_redis_operation("SMEMBERS", "success")
            return result
        except Exception as e:
            track_redis_operation("SMEMBERS", "error")
            logger.error(
                "Redis SMEMBERS failed",
                extra={"name": name, "error": str(e)},
            )
            raise

    async def publish(self, channel: str, message: str) -> int:
        """Publish message to channel.

        Args:
            channel: Channel name.
            message: Message to publish.

        Returns:
            Number of subscribers that received the message.
        """
        await self.connect()

        try:
            with track_redis_operation_duration("PUBLISH"):
                result = await self._pool.publish(channel, message)
            track_redis_operation("PUBLISH", "success")
            return result
        except Exception as e:
            track_redis_operation("PUBLISH", "error")
            logger.error(
                "Redis PUBLISH failed",
                extra={"channel": channel, "error": str(e)},
            )
            raise

    @asynccontextmanager
    async def pipeline(self) -> AsyncGenerator[Any, None]:
        """Create a pipeline for batch operations.

        Yields:
            Pipeline object.

        Example:
            async with client.pipeline() as pipe:
                pipe.set("key1", "value1")
                pipe.set("key2", "value2")
                await pipe.execute()
        """
        await self.connect()
        pipe = self._pool.pipeline()
        try:
            yield pipe
        finally:
            await pipe.execute()

    # Session management
    async def set_session(
        self,
        session_id: str,
        data: Dict[str, Any],
        expire: int = 3600,
    ) -> bool:
        """Store session data.

        Args:
            session_id: Unique session identifier.
            data: Session data dictionary.
            expire: Session expiration in seconds.

        Returns:
            True if session was stored.
        """
        key = f"session:{session_id}"
        json_data = json.dumps(data)
        return await self.set(key, json_data, expire=expire)

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve session data.

        Args:
            session_id: Unique session identifier.

        Returns:
            Session data dictionary or None.
        """
        key = f"session:{session_id}"
        data = await self.get(key)
        if data:
            return json.loads(data)
        return None

    async def delete_session(self, session_id: str) -> int:
        """Delete session data.

        Args:
            session_id: Unique session identifier.

        Returns:
            Number of keys deleted.
        """
        key = f"session:{session_id}"
        return await self.delete(key)

    async def refresh_session(self, session_id: str, expire: int = 3600) -> bool:
        """Refresh session expiration.

        Args:
            session_id: Unique session identifier.
            expire: New expiration time in seconds.

        Returns:
            True if session was refreshed.
        """
        key = f"session:{session_id}"
        return await self.expire(key, expire)


# Global client instance
_redis_client: Optional[RedisClient] = None


def get_redis_client() -> Optional[RedisClient]:
    """Get the global Redis client instance.

    Returns:
        RedisClient instance or None.
    """
    return _redis_client


def init_redis_client(**kwargs) -> RedisClient:
    """Initialize the global Redis client.

    Args:
        **kwargs: Configuration parameters for RedisClient.

    Returns:
        Initialized RedisClient.
    """
    global _redis_client
    _redis_client = RedisClient(**kwargs)
    return _redis_client


def redis_cache(
    expire: int = 300,
    key_prefix: str = "cache",
    key_builder: Optional[Callable[..., str]] = None,
):
    """Decorator for caching function results in Redis.

    Args:
        expire: Cache expiration time in seconds.
        key_prefix: Prefix for cache keys.
        key_builder: Optional custom key builder function.

    Returns:
        Decorator function.

    Example:
        @redis_cache(expire=600)
        async def expensive_operation(user_id: int):
            return await fetch_user_data(user_id)
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            client = get_redis_client()
            if client is None:
                return await func(*args, **kwargs)

            # Build cache key
            if key_builder:
                cache_key = key_builder(*args, **kwargs)
            else:
                # Default key builder using function name and arguments
                sig = hashlib.md5(
                    json.dumps(
                        {
                            "func": func.__name__,
                            "args": args,
                            "kwargs": kwargs,
                        },
                        default=str,
                    ).encode()
                ).hexdigest()
                cache_key = f"{key_prefix}:{func.__name__}:{sig}"

            # Try to get from cache
            try:
                cached = await client.get(cache_key)
                if cached:
                    from ..monitoring.metrics import track_cache_hit

                    track_cache_hit("redis")
                    return json.loads(cached)
            except Exception as e:
                logger.warning(f"Cache get failed: {e}")

            # Execute function
            result = await func(*args, **kwargs)

            # Store in cache
            try:
                await client.set(
                    cache_key,
                    json.dumps(result, default=str),
                    expire=expire,
                )
            except Exception as e:
                logger.warning(f"Cache set failed: {e}")

            from ..monitoring.metrics import track_cache_miss

            track_cache_miss("redis")
            return result

        return async_wrapper

    return decorator


def rate_limit(
    key_prefix: str = "ratelimit",
    max_requests: int = 10,
    window: int = 60,
    identifier: Optional[Callable[..., str]] = None,
):
    """Decorator for rate limiting function calls.

    Args:
        key_prefix: Prefix for rate limit keys.
        max_requests: Maximum requests allowed in window.
        window: Time window in seconds.
        identifier: Optional function to extract rate limit identifier.

    Returns:
        Decorator function.

    Raises:
        RateLimitExceeded: If rate limit is exceeded.

    Example:
        @rate_limit(max_requests=5, window=60)
        async def handle_command(ctx):
            await process_command(ctx)
    """

    class RateLimitExceeded(Exception):
        """Raised when rate limit is exceeded."""

        pass

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            client = get_redis_client()

            # Get identifier
            if identifier:
                rate_key = identifier(*args, **kwargs)
            else:
                # Default: use first argument (often user_id or ctx)
                rate_key = str(args[0]) if args else "global"

            key = f"{key_prefix}:{rate_key}"

            if client:
                try:
                    # Check current count
                    current = await client.get(key)
                    if current and int(current) >= max_requests:
                        from ..monitoring.metrics import track_rate_limit

                        track_rate_limit(func.__name__, rate_key)
                        raise RateLimitExceeded(
                            f"Rate limit exceeded. Try again in {window} seconds."
                        )

                    # Increment counter
                    count = await client.incr(key)
                    if count == 1:
                        # Set expiration on first request
                        await client.expire(key, window)
                except RateLimitExceeded:
                    raise
                except Exception as e:
                    logger.warning(f"Rate limit check failed: {e}")

            return await func(*args, **kwargs)

        return async_wrapper

    return decorator
