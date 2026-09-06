"""
A tiny MongoDB-compatible, file-backed document store.

It implements just enough of the Motor async API (``find``, ``find_one``,
``insert_one/many``, ``update_one``, ``delete_*``, ``count_documents``,
``create_index``) for the repository layer to run identically on top of either
this store or a real MongoDB Atlas cluster.

Purpose: let the whole application (and its tests) run with zero external
services while keeping MongoDB the first-class production backend.
"""
from __future__ import annotations

import asyncio
import copy
import json
import re
import threading
from collections.abc import Iterable
from datetime import date, datetime
from pathlib import Path
from typing import Any

Document = dict[str, Any]


# --------------------------------------------------------------------------- #
# JSON persistence that round-trips datetimes (so range queries keep working)
# --------------------------------------------------------------------------- #

def _json_default(obj: Any) -> Any:
    if isinstance(obj, datetime):
        return {"__dt__": obj.isoformat()}
    if isinstance(obj, date):
        return {"__date__": obj.isoformat()}
    if hasattr(obj, "item"):
        return obj.item()
    return str(obj)


def _json_object_hook(d: dict) -> Any:
    if "__dt__" in d and len(d) == 1:
        return datetime.fromisoformat(d["__dt__"])
    if "__date__" in d and len(d) == 1:
        return datetime.fromisoformat(d["__date__"])
    return d


# --------------------------------------------------------------------------- #
# query matching
# --------------------------------------------------------------------------- #

def _get(doc: Document, dotted: str) -> Any:
    cur: Any = doc
    for part in dotted.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return None
    return cur


def _match_op(value: Any, op: str, operand: Any) -> bool:
    if op == "$eq":
        return value == operand
    if op == "$ne":
        return value != operand
    if op == "$in":
        return value in operand
    if op == "$nin":
        return value not in operand
    if op == "$gt":
        return value is not None and value > operand
    if op == "$gte":
        return value is not None and value >= operand
    if op == "$lt":
        return value is not None and value < operand
    if op == "$lte":
        return value is not None and value <= operand
    if op == "$exists":
        return (value is not None) == bool(operand)
    if op == "$regex":
        flags = 0
        if isinstance(operand, dict):
            pattern = operand.get("$regex", "")
            if "i" in operand.get("$options", ""):
                flags = re.IGNORECASE
        else:
            pattern = operand
        return value is not None and re.search(pattern, str(value), flags) is not None
    raise NotImplementedError(f"query operator {op!r} not supported by memory store")


def _match_field(value: Any, condition: Any) -> bool:
    if isinstance(condition, dict) and any(k.startswith("$") for k in condition):
        for op, operand in condition.items():
            if op == "$options":
                continue
            if op == "$regex" and isinstance(condition, dict):
                if not _match_op(value, "$regex", condition):
                    return False
                continue
            if not _match_op(value, op, operand):
                return False
        return True
    return value == condition


def matches(doc: Document, query: Document) -> bool:
    for key, condition in (query or {}).items():
        if key == "$or":
            if not any(matches(doc, sub) for sub in condition):
                return False
        elif key == "$and":
            if not all(matches(doc, sub) for sub in condition):
                return False
        elif key == "$nor":
            if any(matches(doc, sub) for sub in condition):
                return False
        else:
            if not _match_field(_get(doc, key), condition):
                return False
    return True


def _apply_update(doc: Document, update: Document) -> Document:
    for op, changes in update.items():
        if op == "$set":
            for k, v in changes.items():
                _set_dotted(doc, k, v)
        elif op == "$setOnInsert":
            continue
        elif op == "$inc":
            for k, v in changes.items():
                doc[k] = _get(doc, k) or 0
                doc[k] += v
        elif op == "$push":
            for k, v in changes.items():
                doc.setdefault(k, [])
                doc[k].append(v)
        elif op == "$addToSet":
            for k, v in changes.items():
                doc.setdefault(k, [])
                if v not in doc[k]:
                    doc[k].append(v)
        elif op == "$pull":
            for k, v in changes.items():
                if k in doc and isinstance(doc[k], list):
                    doc[k] = [x for x in doc[k] if x != v]
        elif not op.startswith("$"):
            # replacement document
            doc.clear()
            doc.update(update)
            return doc
        else:
            raise NotImplementedError(f"update operator {op!r} not supported")
    return doc


def _set_dotted(doc: Document, dotted: str, value: Any) -> None:
    parts = dotted.split(".")
    cur = doc
    for p in parts[:-1]:
        cur = cur.setdefault(p, {})
    cur[parts[-1]] = value


# --------------------------------------------------------------------------- #
# result helpers
# --------------------------------------------------------------------------- #

class _Result:
    def __init__(self, inserted_id=None, matched=0, modified=0, upserted_id=None, deleted=0):
        self.inserted_id = inserted_id
        self.matched_count = matched
        self.modified_count = modified
        self.upserted_id = upserted_id
        self.deleted_count = deleted


class _InsertManyResult:
    def __init__(self, ids: list):
        self.inserted_ids = ids


class _Cursor:
    def __init__(self, docs: list[Document]):
        self._docs = docs
        self._sort: list[tuple[str, int]] = []
        self._skip = 0
        self._limit = 0

    def sort(self, key_or_list, direction: int | None = None) -> _Cursor:
        if isinstance(key_or_list, str):
            self._sort = [(key_or_list, direction or 1)]
        else:
            self._sort = list(key_or_list)
        return self

    def skip(self, n: int) -> _Cursor:
        self._skip = n
        return self

    def limit(self, n: int) -> _Cursor:
        self._limit = n
        return self

    def _materialise(self) -> list[Document]:
        docs = self._docs
        for key, direction in reversed(self._sort):
            docs = sorted(
                docs,
                key=lambda d: (_get(d, key) is None, _get(d, key)),
                reverse=direction < 0,
            )
        if self._skip:
            docs = docs[self._skip:]
        if self._limit:
            docs = docs[: self._limit]
        return [copy.deepcopy(d) for d in docs]

    async def to_list(self, length: int | None = None) -> list[Document]:
        docs = self._materialise()
        if length is not None:
            docs = docs[:length]
        return docs

    def __aiter__(self):
        self._iter = iter(self._materialise())
        return self

    async def __anext__(self):
        try:
            return next(self._iter)
        except StopIteration:  # pragma: no cover
            raise StopAsyncIteration from None


# --------------------------------------------------------------------------- #
# collection + database
# --------------------------------------------------------------------------- #

class MemoryCollection:
    def __init__(self, db: MemoryDatabase, name: str):
        self._db = db
        self._name = name
        self._docs: list[Document] = db._data.setdefault(name, [])
        self._unique_indexes: list[list[str]] = []
        self._unique_sets: dict[tuple[str, ...], set] = {}

    # -- indexes ------------------------------------------------------- #
    async def create_index(self, keys, unique: bool = False, **_: Any) -> str:
        if isinstance(keys, str):
            keys = [(keys, 1)]
        fields = [k for k, _ in keys]
        if unique and fields not in self._unique_indexes:
            values = {self._key_tuple(doc, fields) for doc in self._docs}
            if len(values) != len(self._docs):
                raise DuplicateKeyError(f"duplicate key on {fields} in {self._name}")
            self._unique_indexes.append(fields)
            self._unique_sets[tuple(fields)] = values
        return "_".join(f"{f}_{d}" for f, d in keys)

    def _key_tuple(self, doc: Document, fields: tuple[str, ...] | list[str]):
        return tuple(_get(doc, f) for f in fields)

    def _rebuild_unique_set(self, fields: tuple[str, ...]) -> None:
        self._unique_sets[fields] = {self._key_tuple(d, fields) for d in self._docs}

    # -- reads ------------------------------------------------------- #
    def find(self, query: Document | None = None) -> _Cursor:
        query = query or {}
        return _Cursor([d for d in self._docs if matches(d, query)])

    async def find_one(self, query: Document | None = None, sort=None) -> Document | None:
        cur = self.find(query or {})
        if sort:
            cur.sort(sort)
        docs = await cur.to_list(1)
        return docs[0] if docs else None

    async def count_documents(self, query: Document | None = None) -> int:
        query = query or {}
        return sum(1 for d in self._docs if matches(d, query))

    async def distinct(self, key: str, query: Document | None = None) -> list[Any]:
        query = query or {}
        seen: list[Any] = []
        for d in self._docs:
            if matches(d, query):
                v = _get(d, key)
                if v not in seen:
                    seen.append(v)
        return seen

    # -- writes ------------------------------------------------------- #
    def _check_unique(self, doc: Document, ignore_key: dict | None = None) -> None:
        for fields in self._unique_indexes:
            ft = tuple(fields)
            key = self._key_tuple(doc, ft)
            if any(v is None for v in key):
                continue
            existing = self._unique_sets.setdefault(ft, set())
            if key in existing and (ignore_key is None or ignore_key.get(ft) != key):
                raise DuplicateKeyError(f"duplicate key on {fields} in {self._name}")

    def _register_keys(self, doc: Document) -> None:
        for fields in self._unique_indexes:
            ft = tuple(fields)
            self._unique_sets.setdefault(ft, set()).add(self._key_tuple(doc, ft))

    async def insert_one(self, doc: Document) -> _Result:
        doc = copy.deepcopy(doc)
        doc.setdefault("_id", self._db._new_id())
        self._check_unique(doc)
        self._docs.append(doc)
        self._register_keys(doc)
        self._db._touch()
        return _Result(inserted_id=doc["_id"])

    async def insert_many(self, docs: Iterable[Document], ordered: bool = True) -> _InsertManyResult:
        ids = []
        for d in docs:
            d = copy.deepcopy(d)
            d.setdefault("_id", self._db._new_id())
            self._check_unique(d)
            self._docs.append(d)
            self._register_keys(d)
            ids.append(d["_id"])
        self._db._touch()
        return _InsertManyResult(ids)

    async def update_one(self, query: Document, update: Document, upsert: bool = False) -> _Result:
        for d in self._docs:
            if matches(d, query):
                before_keys = {tuple(f): self._key_tuple(d, f) for f in self._unique_indexes}
                _apply_update(d, update)
                self._check_unique(d, ignore_key=before_keys)
                self._reindex_unique()
                self._db._touch()
                return _Result(matched=1, modified=1)
        if upsert:
            base: Document = {}
            for key, cond in query.items():
                if not key.startswith("$") and not isinstance(cond, dict):
                    base[key] = cond
            if "$setOnInsert" in update:
                base.update(update["$setOnInsert"])
            base.setdefault("_id", self._db._new_id())
            _apply_update(base, {k: v for k, v in update.items() if k != "$setOnInsert"})
            self._check_unique(base)
            self._docs.append(base)
            self._register_keys(base)
            self._db._touch()
            return _Result(matched=0, modified=0, upserted_id=base["_id"])
        return _Result(matched=0, modified=0)

    async def update_many(self, query: Document, update: Document) -> _Result:
        n = 0
        for d in self._docs:
            if matches(d, query):
                _apply_update(d, update)
                n += 1
        if n:
            self._reindex_unique()
            self._db._touch()
        return _Result(matched=n, modified=n)

    async def replace_one(self, query: Document, replacement: Document, upsert: bool = False) -> _Result:
        for i, d in enumerate(self._docs):
            if matches(d, query):
                replacement = copy.deepcopy(replacement)
                replacement["_id"] = d["_id"]
                self._docs[i] = replacement
                self._reindex_unique()
                self._db._touch()
                return _Result(matched=1, modified=1)
        if upsert:
            replacement = copy.deepcopy(replacement)
            replacement.setdefault("_id", self._db._new_id())
            self._docs.append(replacement)
            self._register_keys(replacement)
            self._db._touch()
            return _Result(upserted_id=replacement["_id"])
        return _Result()

    def _reindex_unique(self) -> None:
        for fields in self._unique_indexes:
            self._rebuild_unique_set(tuple(fields))

    async def delete_one(self, query: Document) -> _Result:
        for i, d in enumerate(self._docs):
            if matches(d, query):
                self._docs.pop(i)
                self._reindex_unique()
                self._db._touch()
                return _Result(deleted=1)
        return _Result(deleted=0)

    async def delete_many(self, query: Document) -> _Result:
        before = len(self._docs)
        kept = [d for d in self._docs if not matches(d, query)]
        self._db._data[self._name] = kept
        self._docs = kept
        deleted = before - len(kept)
        if deleted:
            self._reindex_unique()
            self._db._touch()
        return _Result(deleted=deleted)

    async def drop(self) -> None:
        self._db._data[self._name] = []
        self._docs = self._db._data[self._name]
        self._unique_sets = {}
        self._db._touch()


class DuplicateKeyError(Exception):
    """Raised on a unique-index violation (mirrors pymongo.errors.DuplicateKeyError)."""


class MemoryDatabase:
    """A named database: a mapping of collection name -> list of documents."""

    def __init__(self, name: str, persist_path: Path | None = None):
        self.name = name
        self._data: dict[str, list[Document]] = {}
        self._collections: dict[str, MemoryCollection] = {}
        self._persist_path = persist_path
        self._autoflush = True
        self._dirty = False
        self._id_counter = 0
        self._lock = threading.Lock()
        if persist_path and persist_path.exists():
            self._load()

    # -- persistence --------------------------------------------------- #
    def _load(self) -> None:
        try:
            raw = json.loads(self._persist_path.read_text(), object_hook=_json_object_hook)
            self._data = raw.get("collections", {})
            self._id_counter = raw.get("id_counter", 0)
        except (json.JSONDecodeError, OSError):
            self._data = {}

    def _touch(self) -> None:
        self._dirty = True
        if self._autoflush:
            self.flush()

    def flush(self) -> None:
        if not self._persist_path or not self._dirty:
            return
        with self._lock:
            payload = {"collections": self._data, "id_counter": self._id_counter}
            tmp = self._persist_path.with_suffix(".tmp")
            tmp.write_text(json.dumps(payload, default=_json_default))
            tmp.replace(self._persist_path)
            self._dirty = False

    def set_autoflush(self, enabled: bool) -> None:
        self._autoflush = enabled
        if enabled:
            self.flush()

    def _new_id(self) -> str:
        self._id_counter += 1
        return f"md_{self._id_counter:012d}"

    # -- Motor-ish accessors ---------------------------------------- #
    def get_collection(self, name: str) -> MemoryCollection:
        if name not in self._collections:
            self._collections[name] = MemoryCollection(self, name)
        return self._collections[name]

    def __getitem__(self, name: str) -> MemoryCollection:
        return self.get_collection(name)

    async def list_collection_names(self) -> list[str]:
        return list(self._data.keys())

    async def command(self, *_args, **_kwargs) -> dict:
        return {"ok": 1}


class MemoryClient:
    """Stand-in for AsyncIOMotorClient."""

    def __init__(self, store_dir: Path):
        self._store_dir = store_dir
        self._dbs: dict[str, MemoryDatabase] = {}

    def get_database(self, name: str) -> MemoryDatabase:
        if name not in self._dbs:
            self._dbs[name] = MemoryDatabase(name, self._store_dir / f"{name}.json")
        return self._dbs[name]

    def __getitem__(self, name: str) -> MemoryDatabase:
        return self.get_database(name)

    async def drop_database(self, name: str) -> None:
        db = self.get_database(name)
        db._data = {}
        db._collections = {}
        db._touch()

    async def admin_ping(self) -> bool:
        return True

    def close(self) -> None:
        for db in self._dbs.values():
            db.flush()


_ = asyncio  # keep import referenced for API parity
