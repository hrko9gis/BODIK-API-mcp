"""
BODIK API MCP Server
"""

import os
import json
import aiohttp
import asyncio
import logging
from typing import Dict, Any, Optional, List

from mcp.server import Server
from mcp.server import NotificationOptions
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

BASE_URL = os.environ.get("BODIK_API_BASE", "https://wapi.bodik.jp")

server = Server("bodik-api-mcp")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === Known apinames (from BODIK API manual) ===
APINAME_LIST = [
    "aed",
    "care_service",
    "hospital",
    "cultural_property",
    "tourism",
    "event",
    "public_wireless_lan",
    "public_toilet",
    "public_facility",
    "fire_hydrant",
    "evacuation_space",
    "population",
    "preschool",
    "food_business_license",
    "school_lunch",
    "school_districts",
]

# -------- Helpers --------
async def _http_get(session: aiohttp.ClientSession, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    url = f"{BASE_URL}{path}"
    logger.info("GET %s params=%s", url, params)
    async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=30)) as resp:
        text = await resp.text()
        if resp.status != 200:
            raise RuntimeError(f"GET {url} -> {resp.status}: {text[:500]}")
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {"raw": text}

async def _http_post(session: aiohttp.ClientSession, path: str, body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    url = f"{BASE_URL}{path}"
    logger.info("POST %s body=%s", url, body)
    headers = {"Content-Type": "application/json"}
    async with session.post(url, headers=headers, json=body or {}, timeout=aiohttp.ClientTimeout(total=30)) as resp:
        text = await resp.text()
        if resp.status != 200:
            raise RuntimeError(f"POST {url} -> {resp.status}: {text[:500]}")
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {"raw": text}

# Extract Feature list and flat records (properties)
def _extract_features(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    try:
        return data.get("resultsets", {}).get("features", [])
    except Exception:
        return []

def _to_records(features: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for f in features:
        props = f.get("properties", {})
        out.append(props)
    return out

# CSV serialization for LLMs / spreadsheets

def _records_to_csv(records: List[Dict[str, Any]], max_cols: int = 60) -> str:
    if not records:
        return ""
    # choose headers as union (bounded)
    headers: List[str] = []
    seen = set()
    for r in records:
        for k in r.keys():
            if k not in seen:
                seen.add(k)
                headers.append(k)
            if len(headers) >= max_cols:
                break
        if len(headers) >= max_cols:
            break
    io = StringIO()
    writer = csv.DictWriter(io, fieldnames=headers, extrasaction="ignore")
    writer.writeheader()
    for r in records:
        writer.writerow(r)
    return io.getvalue()

# -------- Tools --------

async def tool_list_apinames() -> TextContent:
    """List known dataset API names (apiname)."""
    return TextContent(type="text", text=json.dumps({"apiname_list": APINAME_LIST}, ensure_ascii=False, indent=2))

async def tool_list_organizations(apiname: str) -> TextContent:
    """GET /<apiname>/organization — List municipalities that publish the dataset."""
    async with aiohttp.ClientSession() as session:
        data = await _http_get(session, f"/{apiname}/organization")
        return TextContent(type="text", text=json.dumps(data, ensure_ascii=False, indent=2))

async def tool_list_all_organizations() -> TextContent:
    """GET /organization — List all municipalities that publish to BODIK."""
    async with aiohttp.ClientSession() as session:
        data = await _http_get(session, "/organization")
        return TextContent(type="text", text=json.dumps(data, ensure_ascii=False, indent=2))

async def tool_get_config(apiname: str) -> TextContent:
    """GET /config/<apiname> — Retrieve dataset configuration & schema info."""
    async with aiohttp.ClientSession() as session:
        data = await _http_get(session, f"/config/{apiname}")
        return TextContent(type="text", text=json.dumps(data, ensure_ascii=False, indent=2))

async def tool_search_get(apiname: str, params: Optional[Dict[str, Any]] = None) -> TextContent:
    """GET /<apiname> — Search dataset using query params.

    Example params: {"select_type":"data","maxResults":10,"municipalityName":"福岡市"}
    """
    async with aiohttp.ClientSession() as session:
        data = await _http_get(session, f"/{apiname}", params=params or {})
        return TextContent(type="text", text=json.dumps(data, ensure_ascii=False, indent=2))

async def tool_search_post(apiname: str, body: Optional[Dict[str, Any]] = None) -> TextContent:
    """POST /api/<apiname> — Advanced search with JSON body (ranges, etc.)."""
    async with aiohttp.ClientSession() as session:
        data = await _http_post(session, f"/api/{apiname}", body=body or {})
        return TextContent(type="text", text=json.dumps(data, ensure_ascii=False, indent=2))

async def tool_search_get_records(apiname: str, params: Optional[Dict[str, Any]] = None) -> TextContent:
    """GET search but return flattened `properties` list only (LLM-friendly)."""
    async with aiohttp.ClientSession() as session:
        data = await _http_get(session, f"/{apiname}", params=params or {})
        features = _extract_features(data)
        records = _to_records(features)
        return TextContent(type="text", text=json.dumps({"records": records}, ensure_ascii=False, indent=2))

async def tool_search_get_csv(apiname: str, params: Optional[Dict[str, Any]] = None) -> TextContent:
    """GET search then serialize to CSV (header + rows). Useful for quick exports."""
    async with aiohttp.ClientSession() as session:
        data = await _http_get(session, f"/{apiname}", params=params or {})
        features = _extract_features(data)
        records = _to_records(features)
        csv_text = _records_to_csv(records)
        return TextContent(type="text", text=csv_text)

async def tool_search_get_geojson(apiname: str, params: Optional[Dict[str, Any]] = None) -> TextContent:
    """GET search but return only the FeatureCollection under resultsets (GeoJSON)."""
    async with aiohttp.ClientSession() as session:
        data = await _http_get(session, f"/{apiname}", params=params or {})
        fc = data.get("resultsets", {})
        return TextContent(type="text", text=json.dumps(fc, ensure_ascii=False, indent=2))

@server.list_tools()
async def list_tools() -> List[Tool]:
    return [
        Tool(
            {
                "name": "list_apinames",
                "description": "List known dataset API names (apiname).",
                "inputSchema": {"type":"object","properties":{}},
            }
        ),
        Tool(
            {
                "name": "list_organizations",
                "description": "List municipalities that publish the dataset (GET /<apiname>/organization).",
                "inputSchema": {"type":"object","required":["apiname"],"properties":{"apiname":{"type":"string"}}},
            }
        ),
        Tool(
            {
                "name": "list_all_organizations",
                "description": "List all municipalities that publish to BODIK (GET /organization).",
                "inputSchema": {"type":"object","properties":{}},
            }
        ),
        Tool(
            {
                "name": "get_config",
                "description": "Get dataset configuration & schema (GET /config/<apiname>).",
                "inputSchema": {"type":"object","required":["apiname"],"properties":{"apiname":{"type":"string"}}},
            }
        ),
        Tool(
            {
                "name": "search_get",
                "description": "Search dataset (GET /<apiname>) with query parameters.",
                "inputSchema": {"type":"object","required":["apiname"],"properties":{"apiname":{"type":"string"},"params":{"type":"object"}}},
            }
        ),
        Tool(
            {
                "name": "search_post",
                "description": "Advanced search via POST /api/<apiname> with JSON body.",
                "inputSchema": {"type":"object","required":["apiname"],"properties":{"apiname":{"type":"string"},"body":{"type":"object"}}},
            }
        ),
        Tool(
            {
                "name": "search_get_records",
                "description": "Search (GET) and return flattened records list (properties only).",
                "inputSchema": {"type":"object","required":["apiname"],"properties":{"apiname":{"type":"string"},"params":{"type":"object"}}},
            }
        ),
        Tool(
            {
                "name": "search_get_csv",
                "description": "Search (GET) and return CSV text (header + rows).",
                "inputSchema": {"type":"object","required":["apiname"],"properties":{"apiname":{"type":"string"},"params":{"type":"object"}}},
            }
        ),
        Tool(
            {
                "name": "search_get_geojson",
                "description": "Search (GET) and return the FeatureCollection as GeoJSON.",
                "inputSchema": {"type":"object","required":["apiname"],"properties":{"apiname":{"type":"string"},"params":{"type":"object"}}},
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> List[TextContent]:
    if name == "list_apinames":
        result = await tool_list_apinames()

    elif name == "list_organizations":
        result = await tool_list_organizations(arguments["apiname"])

    elif name == "list_all_organizations":
        result = await tool_list_all_organizations()

    elif name == "get_config":
        result = await tool_get_config(arguments["apiname"])

    elif name == "search_get":
        result = await tool_search_get(arguments["apiname"], arguments.get("params"))

    elif name == "search_post":
        result = await tool_search_post(arguments["apiname"], arguments.get("body"))

    elif name == "search_get_records":
        result = await tool_search_get_records(arguments["apiname"], arguments.get("params"))

    elif name == "search_get_csv":
        result = await tool_search_get_csv(arguments["apiname"], arguments.get("params"))

    elif name == "search_get_geojson":
        result = await tool_search_get_geojson(arguments["apiname"], arguments.get("params"))

    else:
        raise ValueError(f"Unknown tool: {name}")

    return [result]


async def main() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="bodik-api-mcp",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    asyncio.run(main())
