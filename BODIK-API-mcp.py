"""
BODIK API MCP Server

- Wraps the public BODIK API (https://wapi.bodik.jp) with MCP tools for dataset discovery and data retrieval.
- Adds helper tools that transform results into LLM-friendly structures (records list, CSV, and GeoJSON passthrough).
- Designed to mirror the patterns used in other sample MCP servers (async, aiohttp, stdio) for easy integration.

Usage (stdio):
  uv run python bodik-api-mcp.py
  # or
  python bodik-api-mcp.py

Test quickly (manual):
  # list known dataset API names (apiname)
  -> call tool: list_apinames
  # list municipalities that publish "aed""""
BODIK API MCP Server (Enhanced for Generative-AI and Full BODIK API Compatibility)

References:
- BODIK API Manual: https://www.bodik.jp/project/bodik-api/bodik-api-manual/
- API Viewer: https://wapi.bodik.jp/apiviewer
- API Search: https://wapi.bodik.jp/apisearch
- Organization List (GET): https://wapi.bodik.jp/organapi
- Organization Search (POST): https://wapi.bodik.jp/organapi_post
- BODIK Python Class Docs:
  - https://www.bodik.jp/project/bodik-api/bodik-api-documents/bodik-api-python1/bodik-api-python-class1-1/
  - https://www.bodik.jp/project/bodik-api/bodik-api-documents/bodik-api-python1/bodik-api-python-class1-2/

This MCP server provides AI-friendly tools for BODIK API dataset discovery, metadata, and data retrieval.
"""

import os
import aiohttp
import asyncio
import json
import logging
import csv
from io import StringIO
from typing import Dict, Any, List, Optional

from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
from mcp.types import Tool, TextContent

BASE_URL = os.environ.get("BODIK_API_BASE", "https://wapi.bodik.jp")
server = Server("bodik-api-mcp")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === Helper functions ===
async def _http_get(session: aiohttp.ClientSession, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    url = f"{BASE_URL}{path}"
    logger.info("GET %s params=%s", url, params)
    async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=30)) as resp:
        text = await resp.text()
        if resp.status != 200:
            raise RuntimeError(f"GET {url} -> {resp.status}: {text[:200]}")
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
            raise RuntimeError(f"POST {url} -> {resp.status}: {text[:200]}")
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {"raw": text}

def _extract_features(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    try:
        return data.get("resultsets", {}).get("features", [])
    except Exception:
        return []

def _to_records(features: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [f.get("properties", {}) for f in features]

def _records_to_csv(records: List[Dict[str, Any]]) -> str:
    if not records:
        return ""
    headers = sorted({k for r in records for k in r.keys()})
    io = StringIO()
    writer = csv.DictWriter(io, fieldnames=headers, extrasaction="ignore")
    writer.writeheader()
    for r in records:
        writer.writerow(r)
    return io.getvalue()

# === Tools ===
async def tool_list_apinames() -> TextContent:
    async with aiohttp.ClientSession() as session:
        data = await _http_get(session, "/apisearch")
        apinames = [api.get("apiname") for api in data.get("result", []) if api.get("apiname")]
        return TextContent(type="text", text=json.dumps({"apiname_list": apinames}, ensure_ascii=False, indent=2))

async def tool_list_organizations() -> TextContent:
    async with aiohttp.ClientSession() as session:
        data = await _http_get(session, "/organapi")
        return TextContent(type="text", text=json.dumps(data, ensure_ascii=False, indent=2))

async def tool_search_organizations(body: Optional[Dict[str, Any]] = None) -> TextContent:
    async with aiohttp.ClientSession() as session:
        data = await _http_post(session, "/organapi_post", body=body or {})
        return TextContent(type="text", text=json.dumps(data, ensure_ascii=False, indent=2))

async def tool_get_apiviewer(apiname: str) -> TextContent:
    async with aiohttp.ClientSession() as session:
        data = await _http_get(session, f"/apiviewer/{apiname}")
        return TextContent(type="text", text=json.dumps(data, ensure_ascii=False, indent=2))

async def tool_search_get(apiname: str, params: Optional[Dict[str, Any]] = None) -> TextContent:
    async with aiohttp.ClientSession() as session:
        data = await _http_get(session, f"/{apiname}", params=params or {})
        return TextContent(type="text", text=json.dumps(data, ensure_ascii=False, indent=2))

async def tool_search_post(apiname: str, body: Optional[Dict[str, Any]] = None) -> TextContent:
    async with aiohttp.ClientSession() as session:
        data = await _http_post(session, f"/api/{apiname}", body=body or {})
        return TextContent(type="text", text=json.dumps(data, ensure_ascii=False, indent=2))

async def tool_search_get_records(apiname: str, params: Optional[Dict[str, Any]] = None) -> TextContent:
    async with aiohttp.ClientSession() as session:
        data = await _http_get(session, f"/{apiname}", params=params or {})
        features = _extract_features(data)
        records = _to_records(features)
        return TextContent(type="text", text=json.dumps({"records": records}, ensure_ascii=False, indent=2))

async def tool_search_get_csv(apiname: str, params: Optional[Dict[str, Any]] = None) -> TextContent:
    async with aiohttp.ClientSession() as session:
        data = await _http_get(session, f"/{apiname}", params=params or {})
        csv_text = _records_to_csv(_to_records(_extract_features(data)))
        return TextContent(type="text", text=csv_text)

async def tool_list_tools() -> TextContent:
    tools_info = [{"name": t.name, "description": t.description, "inputSchema": t.inputSchema} for t in server.tools]
    return TextContent(type="text", text=json.dumps({"tools": tools_info}, ensure_ascii=False, indent=2))

# === Register Tools ===
server.add_tool(Tool(name="list_apinames", description="List all available BODIK dataset API names.", inputSchema={"type":"object","properties":{}}), tool_list_apinames)
server.add_tool(Tool(name="list_organizations", description="List all organizations providing datasets (GET /organapi).", inputSchema={"type":"object","properties":{}}), tool_list_organizations)
server.add_tool(Tool(name="search_organizations", description="Search organizations by conditions (POST /organapi_post).", inputSchema={"type":"object","properties":{"body":{"type":"object"}}}), tool_search_organizations)
server.add_tool(Tool(name="get_apiviewer", description="Retrieve API metadata and schema info (GET /apiviewer/<apiname>).", inputSchema={"type":"object","required":["apiname"],"properties":{"apiname":{"type":"string"}}}), tool_get_apiviewer)
server.add_tool(Tool(name="search_get", description="Search dataset via GET /<apiname>.", inputSchema={"type":"object","required":["apiname"],"properties":{"apiname":{"type":"string"},"params":{"type":"object"}}}), tool_search_get)
server.add_tool(Tool(name="search_post", description="Search dataset via POST /api/<apiname>.", inputSchema={"type":"object","required":["apiname"],"properties":{"apiname":{"type":"string"},"body":{"type":"object"}}}), tool_search_post)
server.add_tool(Tool(name="search_get_records", description="GET search and return properties only (records).", inputSchema={"type":"object","required":["apiname"],"properties":{"apiname":{"type":"string"},"params":{"type":"object"}}}), tool_search_get_records)
server.add_tool(Tool(name="search_get_csv", description="GET search and return CSV format (header + rows).", inputSchema={"type":"object","required":["apiname"],"properties":{"apiname":{"type":"string"},"params":{"type":"object"}}}), tool_search_get_csv)
server.add_tool(Tool(name="list_tools", description="List all available tools with details.", inputSchema={"type":"object","properties":{}}), tool_list_tools)

# === Entry Point ===
async def main() -> None:
    from mcp.server.stdio import stdio_server
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="bodik-api-mcp",
                server_version="2.0.0",
                capabilities=server.get_capabilities(notification_options=NotificationOptions())
            )
        )

if __name__ == "__main__":
    asyncio.run(main())

  -> call tool: list_organizations {"apiname":"aed"}
  # simple search (GET) for AEDs in Fukuoka City, 10 rows
  -> call tool: search_get {"apiname":"aed", "params":{"select_type":"data","maxResults":10,"municipalityName":"福岡市"}}
  # advanced search (POST) – numeric range example
  -> call tool: search_post {"apiname":"evacuation_space","body":{"maxOccupancyCapacity":{"gte":1000,"lte":2000}}}
  # get dataset schema/config
  -> call tool: get_config {"apiname":"aed"}
  # convert a GET search directly to a CSV string (for LLM consumption)
  -> call tool: search_get_csv {"apiname":"aed","params":{"maxResults":5}}

Notes:
- Endpoints are documented at https://www.bodik.jp/project/bodik-api/bodik-api-manual/ and Swagger at https://wapi.bodik.jp/docs
- BODIK API returns FeatureCollection-like structures under data.resultsets; this server extracts `properties` for tabular representations.
- This server does not require an API key as of the public docs (subject to change).
"""

import os
import aiohttp
import asyncio
import json
import logging
import csv
from io import StringIO
from typing import Dict, Any, List, Optional, Tuple

from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
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

# Register tools
server.add_tool(Tool(name="list_apinames", description="List known dataset API names (apiname).", inputSchema={"type":"object","properties":{}},) , tool_list_apinames)
server.add_tool(Tool(name="list_organizations", description="List municipalities that publish the dataset (GET /<apiname>/organization).", inputSchema={"type":"object","required":["apiname"],"properties":{"apiname":{"type":"string"}}},) , tool_list_organizations)
server.add_tool(Tool(name="list_all_organizations", description="List all municipalities that publish to BODIK (GET /organization).", inputSchema={"type":"object","properties":{}},) , tool_list_all_organizations)
server.add_tool(Tool(name="get_config", description="Get dataset configuration & schema (GET /config/<apiname>).", inputSchema={"type":"object","required":["apiname"],"properties":{"apiname":{"type":"string"}}},) , tool_get_config)
server.add_tool(Tool(name="search_get", description="Search dataset (GET /<apiname>) with query parameters.", inputSchema={"type":"object","required":["apiname"],"properties":{"apiname":{"type":"string"},"params":{"type":"object"}}},) , tool_search_get)
server.add_tool(Tool(name="search_post", description="Advanced search via POST /api/<apiname> with JSON body.", inputSchema={"type":"object","required":["apiname"],"properties":{"apiname":{"type":"string"},"body":{"type":"object"}}},) , tool_search_post)
server.add_tool(Tool(name="search_get_records", description="Search (GET) and return flattened records list (properties only).", inputSchema={"type":"object","required":["apiname"],"properties":{"apiname":{"type":"string"},"params":{"type":"object"}}},) , tool_search_get_records)
server.add_tool(Tool(name="search_get_csv", description="Search (GET) and return CSV text (header + rows).", inputSchema={"type":"object","required":["apiname"],"properties":{"apiname":{"type":"string"},"params":{"type":"object"}}},) , tool_search_get_csv)
server.add_tool(Tool(name="search_get_geojson", description="Search (GET) and return the FeatureCollection as GeoJSON.", inputSchema={"type":"object","required":["apiname"],"properties":{"apiname":{"type":"string"},"params":{"type":"object"}}},) , tool_search_get_geojson)


async def main() -> None:
    # stdio server (same pattern as other MCP servers)
    from mcp.server.stdio import stdio_server

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="bodik-api-mcp",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={}
                )
            )
        )

if __name__ == "__main__":
    asyncio.run(main())
