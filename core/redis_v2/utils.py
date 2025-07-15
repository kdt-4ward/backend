from core.redis_v2.redis import redis_client

def acquire_lock(key: str, expire: int = 30) -> bool:
    return redis_client.set(key, "1", nx=True, ex=expire)

def release_lock(key: str):
    redis_client.delete(key)