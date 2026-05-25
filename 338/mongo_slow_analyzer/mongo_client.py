from typing import Dict, Iterator, List, Optional

try:
    from pymongo import MongoClient
    from pymongo.collection import Collection
    from pymongo.errors import ConfigurationError, OperationFailure
except ImportError:  # pragma: no cover
    MongoClient = None  # type: ignore
    Collection = None  # type: ignore
    ConfigurationError = Exception
    OperationFailure = Exception


def connect(cfg: Dict):
    if MongoClient is None:
        raise RuntimeError("pymongo 未安装，请先 pip install pymongo")
    username = cfg.get("username") or ""
    password = cfg.get("password") or ""
    auth_source = cfg.get("auth_source") or "admin"
    host = cfg.get("host", "localhost")
    port = int(cfg.get("port", 27017))

    if username:
        uri = "mongodb://{user}:{pwd}@{host}:{port}/?authSource={src}".format(
            user=username, pwd=password, host=host, port=port, src=auth_source
        )
    else:
        uri = "mongodb://{host}:{port}".format(host=host, port=port)

    return MongoClient(uri, serverSelectionTimeoutMS=3000)


def list_databases(client: MongoClient) -> List[str]:
    try:
        return [d for d in client.list_database_names() if d not in ("admin", "config", "local")]
    except OperationFailure:
        return []


def list_collections(client: MongoClient, db: str) -> List[str]:
    return client[db].list_collection_names()


def get_collection(client: MongoClient, db: str, collection: str) -> Collection:
    return client[db][collection]


def get_profile_collection(client: MongoClient, db: str) -> Collection:
    return client[db]["system.profile"]


def enable_profiling(client: MongoClient, db: str, level: int = 1, slow_ms: int = 100) -> Dict:
    return client[db].command("profile", level, slowms=slow_ms)


def disable_profiling(client: MongoClient, db: str) -> Dict:
    return client[db].command("profile", 0)


def fetch_profile_entries(
    client: MongoClient,
    db: str,
    min_ms: int = 100,
    limit: int = 1000,
    op_filter: Optional[Dict] = None,
) -> Iterator[Dict]:
    coll = get_profile_collection(client, db)
    query = {"millis": {"$gte": min_ms}}
    if op_filter:
        query.update(op_filter)
    for doc in coll.find(query).sort("ts", -1).limit(limit):
        yield doc


def get_collection_indexes(client: MongoClient, db: str, collection: str) -> List[Dict]:
    try:
        return list(client[db][collection].list_indexes())
    except OperationFailure:
        return []


def get_collection_stats(client: MongoClient, db: str, collection: str) -> Dict:
    try:
        return client[db].command("collStats", collection)
    except OperationFailure:
        return {}


def get_shard_info(client: MongoClient) -> Dict:
    info = {"is_sharded": False, "shards": [], "databases": {}}
    try:
        config_db = client["config"]
        shards = list(config_db["shards"].find())
        if shards:
            info["is_sharded"] = True
            info["shards"] = shards
        info["databases"] = {
            d["_id"]: d for d in config_db["databases"].find()
        }
    except OperationFailure:
        pass
    return info


def get_shard_key(client: MongoClient, db: str, collection: str) -> Optional[Dict]:
    try:
        cfg = client["config"]["collections"].find_one({"_id": "{}.{}".format(db, collection)})
        return cfg
    except OperationFailure:
        return None


def get_chunk_distribution(client: MongoClient, db: str, collection: str) -> List[Dict]:
    ns = "{}.{}".format(db, collection)
    try:
        chunks = list(client["config"]["chunks"].find({"ns": ns}))
        by_shard: Dict[str, int] = {}
        for c in chunks:
            by_shard[c.get("shard", "unknown")] = by_shard.get(c.get("shard", "unknown"), 0) + 1
        return [{"shard": sh, "chunks": n} for sh, n in by_shard.items()]
    except OperationFailure:
        return []


def get_explain_result(
    client: MongoClient,
    db: str,
    collection: str,
    command: Dict,
    verbosity: str = "executionStats",
) -> Dict:
    """执行 explain 并返回结果。

    Args:
        command: 原始查询命令，例如 {"find": "users", "filter": {...}, "sort": {...}}
    """
    try:
        if "find" in command:
            cmd = {
                "explain": command,
                "verbosity": verbosity,
                "$db": db,
            }
            return client[db].command(cmd)
    except OperationFailure:
        pass
    return {}
