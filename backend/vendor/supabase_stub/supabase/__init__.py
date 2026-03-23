from __future__ import annotations

import copy
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional
from uuid import uuid4


# In-memory DB shared across all stub clients.
_DB: Dict[str, List[dict[str, Any]]] = {"recruiters": []}


def reset_db() -> None:
    _DB.clear()
    _DB.update({"recruiters": []})


@dataclass
class ExecResult:
    data: Any
    status_code: int = 200


class TableQuery:
    def __init__(self, table_name: str):
        self._table_name = table_name
        self._filters: List[tuple[str, Any]] = []
        self._select: str = "*"
        self._insert_rows: Optional[List[dict[str, Any]]] = None
        self._update_fields: Optional[dict[str, Any]] = None
        self._single: bool = False

    def _reset_query_state(self) -> None:
        """
        Reset internal query builder state.

        Real Supabase clients return new query builders; this stub keeps state
        on the instance, so we must clear it after each execute().
        """
        self._filters = []
        self._select = "*"
        self._insert_rows = None
        self._update_fields = None
        self._single = False

    def from_(self, *_args: Any, **_kwargs: Any) -> "TableQuery":
        # compatibility: allow `client.from_("recruiters")`
        return self

    def select(self, columns: str = "*") -> "TableQuery":
        self._select = columns
        return self

    def eq(self, column: str, value: Any) -> "TableQuery":
        self._filters.append((column, value))
        return self

    def insert(self, data: dict[str, Any] | List[dict[str, Any]]) -> "TableQuery":
        if isinstance(data, list):
            self._insert_rows = data
        else:
            self._insert_rows = [data]
        return self

    def update(self, data: dict[str, Any]) -> "TableQuery":
        self._update_fields = data
        return self

    def single(self) -> "TableQuery":
        self._single = True
        return self

    def execute(self) -> ExecResult:
        global _DB

        rows = _DB.get(self._table_name, [])

        def _apply_filters(input_rows: List[dict[str, Any]]) -> List[dict[str, Any]]:
            for col, val in self._filters:
                input_rows = [r for r in input_rows if r.get(col) == val]
            return input_rows

        if self._insert_rows is not None:
            inserted: List[dict[str, Any]] = []
            for row in self._insert_rows:
                new_row = copy.deepcopy(row)
                if "id" not in new_row or not new_row["id"]:
                    new_row["id"] = str(uuid4())
                # Apply simple defaults
                new_row.setdefault("created_at", datetime.utcnow())

                # Enforce unique email if present
                email = new_row.get("email")
                if email is not None:
                    for existing in rows:
                        if existing.get("email") == email:
                            raise ValueError("duplicate key value violates unique constraint \"recruiters_email_key\"")

                rows.append(new_row)
                inserted.append(copy.deepcopy(new_row))

            _DB[self._table_name] = rows
            result = ExecResult(data=inserted, status_code=201)
            self._reset_query_state()
            return result

        if self._update_fields is not None:
            filtered = _apply_filters(rows)
            updated: List[dict[str, Any]] = []
            for i, r in enumerate(rows):
                if r in filtered:
                    for k, v in self._update_fields.items():
                        r[k] = v
                    updated.append(copy.deepcopy(r))

            result = ExecResult(data=updated, status_code=200)
            self._reset_query_state()
            return result

        # SELECT path
        filtered = _apply_filters(rows)
        if self._single:
            if not filtered:
                result = ExecResult(data=None, status_code=200)
                self._reset_query_state()
                return result
            result = ExecResult(data=copy.deepcopy(filtered[0]), status_code=200)
            self._reset_query_state()
            return result
        result = ExecResult(data=copy.deepcopy(filtered), status_code=200)
        self._reset_query_state()
        return result


class SupabaseClient:
    def __init__(self, url: str, key: str):
        self.url = url
        self.key = key

    def table(self, table_name: str) -> TableQuery:
        return TableQuery(table_name)

    def from_(self, table_name: str) -> TableQuery:
        return TableQuery(table_name)


def create_client(url: str, key: str, *args: Any, **kwargs: Any) -> SupabaseClient:
    """
    Local stub for `supabase.create_client`.

    Supports only the minimal table/CRUD operations needed by the unit tests
    (auth register/login/refresh) for this project scaffold.
    """

    return SupabaseClient(url=url, key=key)

