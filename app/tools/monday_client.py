"""Resilient, strictly read-only Monday.com GraphQL API v2 client.

Features:
- Dynamic cursor-based pagination (fetches 100% of board items)
- Concurrent multi-board fetching (§1.1)
- Reusable connection pooling (httpx.Limits(max_connections=10))
- Multi-tier caching integration (app/cache.py)
- Retrieval integrity verification (Unique Item IDs == Raw Items Retrieved)
- Exponential backoff with jitter on 429 and 5xx errors
- Board schema discovery & column metadata extraction
- Last refresh timestamp tracking and degraded health reporting
- STRICTLY READ-ONLY: Never generates mutations or write operations
"""

from __future__ import annotations

import os
import asyncio
import datetime
import logging
from typing import Any, Dict, List, Optional, Tuple

import httpx
from app.config import settings
from app.cache import get_cached_board_items, set_cached_board_items

logger = logging.getLogger("monday_client")


class MondayClient:
    """Async client for Monday.com GraphQL API v2 with resilient cursor pagination & caching."""

    def __init__(
        self,
        api_token: Optional[str] = None,
        api_url: Optional[str] = None,
        max_retries: Optional[int] = None,
        backoff_factor: Optional[float] = None,
        timeout: Optional[float] = None
    ):
        self.api_token = api_token or settings.MONDAY_API_TOKEN
        self.api_url = api_url or settings.MONDAY_API_URL
        self.max_retries = max_retries or settings.MAX_RETRIES
        self.backoff_factor = backoff_factor or settings.RETRY_BACKOFF_FACTOR
        self.timeout = timeout or settings.REQUEST_TIMEOUT
        
        # Shared connection pool
        self._http_client: Optional[httpx.AsyncClient] = None

        # State tracking
        self.last_refresh_timestamps: Dict[str, str] = {}
        self.retrieval_warnings: List[str] = []

    def _get_http_client(self) -> httpx.AsyncClient:
        """Get or initialize reusable AsyncClient with connection limits."""
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(
                timeout=self.timeout,
                limits=httpx.Limits(max_connections=10, max_keepalive_connections=5)
            )
        return self._http_client

    async def close(self) -> None:
        """Close shared HTTP client pool."""
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()

    def _get_token(self) -> str:
        """Dynamically resolve active API token from Streamlit Cloud secrets, os.environ, or instance."""
        # 1. Check Streamlit Cloud secrets
        try:
            import streamlit as st
            if hasattr(st, "secrets"):
                for key in ("MONDAY_API_TOKEN", "monday_api_token", "MONDAY_TOKEN", "monday_token"):
                    if key in st.secrets:
                        tok = str(st.secrets[key]).strip()
                        if tok and tok != "mock_monday_token":
                            return tok
        except Exception:
            pass

        # 2. Check os.environ
        for key in ("MONDAY_API_TOKEN", "monday_api_token", "MONDAY_TOKEN", "monday_token"):
            tok = os.getenv(key)
            if tok and tok.strip() and tok != "mock_monday_token":
                return tok.strip()

        # 3. Check instance token
        if self.api_token and self.api_token.strip() and self.api_token != "mock_monday_token":
            return self.api_token.strip()

        return ""

    def _get_headers(self) -> Dict[str, str]:
        """Construct secure HTTP headers. API token is never logged."""
        return {
            "Authorization": self._get_token(),
            "Content-Type": "application/json",
            "API-Version": "2024-01"
        }

    async def _execute_query(self, query: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute a strictly read-only GraphQL query with exponential backoff."""
        active_token = self._get_token()
        if not active_token or active_token == "mock_monday_token":
            logger.warning("No live MONDAY_API_TOKEN configured. Client operating in mock/fallback mode.")

        # Safety Check: Guarantee no mutations
        if "mutation" in query.lower():
            raise PermissionError("Write mutations are strictly prohibited. MondayClient is strictly read-only.")

        payload: Dict[str, Any] = {"query": query}
        if variables:
            payload["variables"] = variables

        delay = self.backoff_factor
        last_exception = None
        client = self._get_http_client()

        for attempt in range(1, self.max_retries + 1):
            try:
                response = await client.post(
                    self.api_url,
                    json=payload,
                    headers=self._get_headers()
                )

                if response.status_code == 429:
                    retry_after = float(response.headers.get("Retry-After", delay))
                    logger.warning(f"Monday API Rate Limit (429). Backing off for {retry_after:.2f}s (Attempt {attempt}/{self.max_retries})")
                    await asyncio.sleep(retry_after)
                    delay *= 2
                    continue

                if response.status_code >= 500:
                    logger.warning(f"Monday API Server Error ({response.status_code}). Retrying in {delay:.2f}s (Attempt {attempt}/{self.max_retries})")
                    await asyncio.sleep(delay)
                    delay *= 2
                    continue

                response.raise_for_status()
                data = response.json()

                if "errors" in data:
                    err_msg = "; ".join([e.get("message", "Unknown GraphQL error") for e in data["errors"]])
                    logger.error(f"Monday GraphQL error: {err_msg}")
                    raise RuntimeError(f"Monday GraphQL API Error: {err_msg}")

                return data

            except (httpx.RequestError, httpx.HTTPStatusError) as e:
                last_exception = e
                logger.warning(f"Network error communicating with Monday API: {e}. Retrying in {delay:.2f}s...")
                await asyncio.sleep(delay)
                delay *= 2

        logger.error(f"Failed to execute Monday query after {self.max_retries} attempts.")
        raise RuntimeError(f"Failed to query Monday.com API after {self.max_retries} retries: {last_exception}")

    async def fetch_board_schema(self, board_id: str) -> Dict[str, Any]:
        """Fetch board schema including column IDs, titles, and types."""
        query = """
        query GetBoardSchema($board_id: [ID!]) {
            boards(ids: $board_id) {
                id
                name
                columns {
                    id
                    title
                    type
                    settings_str
                }
            }
        }
        """
        data = await self._execute_query(query, {"board_id": [board_id]})
        boards = data.get("data", {}).get("boards", [])
        if not boards:
            raise ValueError(f"Board with ID {board_id} not found.")

        board = boards[0]
        logger.info(f"Discovered schema for board '{board.get('name')}' ({board_id}) with {len(board.get('columns', []))} columns.")
        return {
            "board_id": str(board.get("id")),
            "board_name": board.get("name"),
            "columns": board.get("columns", [])
        }

    async def fetch_board_items(
        self,
        board_id: str,
        limit: int = 100,
        use_cache: bool = False
    ) -> List[Dict[str, Any]]:
        """Fetch all items from a board using dynamic cursor-based pagination and caching."""
        # 1. Check cache first (§2.1)
        if use_cache:
            cached = await get_cached_board_items(str(board_id))
            if cached is not None:
                logger.info(f"Loaded {len(cached)} items for board {board_id} from cache.")
                return cached

        initial_query = """
        query GetInitialBoardItems($board_id: [ID!], $limit: Int!) {
            boards(ids: $board_id) {
                id
                name
                items_page(limit: $limit) {
                    cursor
                    items {
                        id
                        name
                        column_values {
                            id
                            text
                            value
                            type
                        }
                    }
                }
            }
        }
        """

        next_page_query = """
        query GetNextBoardItems($cursor: String!, $limit: Int!) {
            next_items_page(cursor: $cursor, limit: $limit) {
                cursor
                items {
                    id
                    name
                    column_values {
                        id
                        text
                        value
                        type
                    }
                }
            }
        }
        """

        raw_items: List[Dict[str, Any]] = []

        try:
            # Initial Page
            init_data = await self._execute_query(initial_query, {"board_id": [board_id], "limit": limit})
            boards = init_data.get("data", {}).get("boards", [])
            if not boards:
                raise ValueError(f"Board with ID {board_id} not found.")

            items_page = boards[0].get("items_page", {})
            raw_items.extend(items_page.get("items", []))
            cursor = items_page.get("cursor")

            # Cursor Pagination Loop
            page_count = 1
            while cursor:
                page_count += 1
                next_data = await self._execute_query(next_page_query, {"cursor": cursor, "limit": limit})
                next_page = next_data.get("data", {}).get("next_items_page", {})
                next_items = next_page.get("items", [])
                
                if not next_items:
                    break

                raw_items.extend(next_items)
                cursor = next_page.get("cursor")

            # Record successful refresh timestamp
            now_iso = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            self.last_refresh_timestamps[str(board_id)] = now_iso

        except Exception as exc:
            logger.error(f"Error retrieving board items for {board_id}: {exc}")
            raise

        # Transform and verify retrieval integrity
        seen_ids = set()
        duplicate_ids = []
        parsed_items: List[Dict[str, Any]] = []

        for item in raw_items:
            item_id = str(item.get("id"))
            if item_id in seen_ids:
                duplicate_ids.append(item_id)
            seen_ids.add(item_id)

            cols_dict = {}
            for col in item.get("column_values", []):
                cols_dict[col.get("id")] = {
                    "text": col.get("text"),
                    "value": col.get("value"),
                    "type": col.get("type")
                }

            parsed_items.append({
                "item_id": item_id,
                "item_name": item.get("name"),
                "columns": cols_dict
            })

        # Integrity check
        if duplicate_ids:
            warning_msg = f"Board {board_id} has {len(duplicate_ids)} duplicate item IDs detected in API response."
            logger.warning(warning_msg)
            self.retrieval_warnings.append(warning_msg)

        logger.info(f"Retrieved {len(parsed_items)} items from board {board_id} (Unique IDs: {len(seen_ids)}) across {page_count} page(s).")
        
        # 2. Write to cache (§2.1)
        await set_cached_board_items(str(board_id), parsed_items)
        return parsed_items

    async def fetch_all_boards(
        self,
        board_ids: List[str],
        use_cache: bool = False
    ) -> Dict[str, Dict[str, Any]]:
        """Fetch multiple boards concurrently (§1.1).
        
        Each board's cursor pagination stays sequential internally,
        but independent boards are fetched in parallel wall-clock time.
        """
        results = await asyncio.gather(
            *(self.fetch_board_items(board_id, use_cache=use_cache) for board_id in board_ids),
            return_exceptions=True
        )
        out: Dict[str, Dict[str, Any]] = {}
        for board_id, result in zip(board_ids, results):
            if isinstance(result, Exception):
                logger.error(f"Partial failure fetching board {board_id}: {result}")
                out[str(board_id)] = {"error": str(result), "items": []}
            else:
                out[str(board_id)] = {"error": None, "items": result}
        return out

    async def health_check(self) -> Dict[str, Any]:
        """Perform comprehensive connectivity and board reachability health check."""
        deals_id = settings.MONDAY_DEALS_BOARD_ID
        wo_id = settings.MONDAY_WORK_ORDERS_BOARD_ID

        health_res = {
            "status": "healthy",
            "api_reachable": False,
            "boards": {
                "deals": {"board_id": deals_id, "reachable": False, "item_count": 0, "last_refresh": self.last_refresh_timestamps.get(deals_id)},
                "work_orders": {"board_id": wo_id, "reachable": False, "item_count": 0, "last_refresh": self.last_refresh_timestamps.get(wo_id)}
            },
            "errors": []
        }

        try:
            deals_items = await self.fetch_board_items(deals_id, limit=25)
            health_res["boards"]["deals"]["reachable"] = True
            health_res["boards"]["deals"]["item_count"] = len(deals_items)
            health_res["boards"]["deals"]["last_refresh"] = self.last_refresh_timestamps.get(deals_id)
            health_res["api_reachable"] = True
        except Exception as exc:
            health_res["boards"]["deals"]["error"] = str(exc)
            health_res["errors"].append(f"Deals Board ({deals_id}) error: {exc}")

        try:
            wo_items = await self.fetch_board_items(wo_id, limit=25)
            health_res["boards"]["work_orders"]["reachable"] = True
            health_res["boards"]["work_orders"]["item_count"] = len(wo_items)
            health_res["boards"]["work_orders"]["last_refresh"] = self.last_refresh_timestamps.get(wo_id)
            health_res["api_reachable"] = True
        except Exception as exc:
            health_res["boards"]["work_orders"]["error"] = str(exc)
            health_res["errors"].append(f"Work Orders Board ({wo_id}) error: {exc}")

        except Exception as exc:
            health_res["errors"].append(f"Health check execution error: {exc}")

        # Determine overall status
        if health_res["boards"]["deals"]["reachable"] and health_res["boards"]["work_orders"]["reachable"]:
            health_res["status"] = "healthy"
        elif health_res["boards"]["deals"]["reachable"] or health_res["boards"]["work_orders"]["reachable"]:
            health_res["status"] = "degraded"
        else:
            health_res["status"] = "unreachable"

        return health_res


monday_client = MondayClient()
