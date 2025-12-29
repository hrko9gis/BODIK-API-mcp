import httpx
import asyncio
import json
import logging
from mcp.server import Server
from mcp.types import Tool, TextContent
from mcp.server.stdio import stdio_server
from typing import Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 1. サーバーの初期化
server = Server("bodik-api-server")

BASE_URL = "https://wapi.bodik.jp"
LIST_API_URL = f"{BASE_URL}/api/list"

# デフォルトで返却する最小限のフィールドリスト
DEFAULT_FIELDS = ["name", "address", "telNumber", "lat", "lon"]

# 2. ツール一覧の定義 (list_tools)
@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="get_api_list",
            description=(
                "BODIK APIで現在利用可能な全てのデータセット名(apiname)の一覧を取得します。"
                "最初に使用して、目的のデータセット名を見つけてください。"
            ),
            inputSchema={"type": "object", "properties": {}}
        ),
        Tool(
            name="get_municipality_code",
            description=(
                "自治体名からその自治体コードを検索します。部分一致検索が可能です。"
                "search_datasetでmunicipalityCodeを使用して正確に絞り込みたい場合に使用してください。"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "q": {"type": "string", "description": "検索したい自治体名（例：福岡市、新宿区）"},
                },
                "required": ["q"],
            }
        ),
        Tool(
            name="get_all_organizations",
            description="APIを提供している全ての自治体名と自治体コードの一覧を取得します。",
            inputSchema={"type": "object", "properties": {}}
        ),
        Tool(
            name="get_dataset_config",
            description=(
                "【重要：検索前に推奨】データセットに含まれる項目(fields)を確認します。"
                "search_datasetの実行前にこれで項目名を確認し、必要な項目だけをfields引数に指定してください。"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "apiname": {"type": "string", "description": "API名"},
                },
                "required": ["apiname"],
            }
        ),
        Tool(
            name="get_organization",
            description="特定のデータセット(apiname)を提供している組織の一覧を取得します。",
            inputSchema={
                "type": "object",
                "properties": {
                    "apiname": {"type": "string", "description": "API名"},
                },
                "required": ["apiname"],
            }
        ),
        Tool(
            name="search_dataset",
            description=(
                "指定したデータセットを検索します。データ量節約のため、事前にget_dataset_configで項目名を確認し、"
                "引数'fields'に取得したい項目をリストで指定することを強く推奨します。"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "apiname": {"type": "string", "description": "API名"},
                    "fields": {
                        "type": "array", 
                        "items": {"type": "string"}, 
                        "description": "取得したいフィールド名のリスト。未指定時は名称、住所、電話、座標のみ返します。"
                    },
                    "maxResults": {"type": "integer", "description": "最大取得件数 (デフォルト: 10)"},
                    "lat": {"type": "number", "description": "緯度"},
                    "lon": {"type": "number", "description": "経度"},
                    "distance": {"type": "integer", "description": "中心からの距離(m)"},
                    "municipalityCode": {"type": "string", "description": "自治体コード"},
                    "municipalityName": {"type": "string", "description": "自治体名"},
                    "name": {"type": "string", "description": "施設等の名称"},
                },
                "required": ["apiname"],
            }
        )
    ]

# 3. ツール実行ロジック (call_tool)
@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            if name == "get_api_list":
                resp = await client.get(LIST_API_URL)
                resp.raise_for_status()
                data = resp.json()
                lines = [f"- {i.get('apiname')}: {i.get('description')}" for i in data] if isinstance(data, list) else []
                text = "利用可能なAPI一覧:\n\n" + "\n".join(lines)
                text += "\n\n--- 次のステップ ---\n1. apinameを選び 'get_dataset_config' で取得項目を確認\n2. 'get_municipality_code' で自治体コードを確認（任意）\n3. 'search_dataset' で fields を指定して検索"
                logger.info(f"get_api_list: {text}")
                return [TextContent(type="text", text=text)]

            elif name == "get_municipality_code":
                q = arguments.get("q")
                resp = await client.get(f"{BASE_URL}/organization")
                resp.raise_for_status()
                all_orgs = resp.json()
                # 部分一致で絞り込み
                matched = [o for o in all_orgs if q in o.get("organ_name")]
                return [TextContent(type="text", text=json.dumps(matched, indent=2, ensure_ascii=False))]

            elif name == "get_all_organizations":
                resp = await client.get(f"{BASE_URL}/organization")
                resp.raise_for_status()
                return [TextContent(type="text", text=json.dumps(resp.json(), indent=2, ensure_ascii=False))]

            elif name == "get_dataset_config":
                apiname = arguments.get("apiname")
                resp = await client.get(f"{BASE_URL}/config/{apiname}")
                resp.raise_for_status()
                data = resp.json()
                
                return [TextContent(type="text", text=json.dumps(data, indent=2, ensure_ascii=False))]

            elif name == "get_organization":
                apiname = arguments.get("apiname")
                resp = await client.get(f"{BASE_URL}/{apiname}/organization")
                resp.raise_for_status()
                return [TextContent(type="text", text=json.dumps(resp.json(), indent=2, ensure_ascii=False))]

            elif name == "search_dataset":
                args_copy = dict(arguments)
                apiname = args_copy.pop("apiname")
                fields_provided = "fields" in args_copy
                selected_fields = args_copy.pop("fields", DEFAULT_FIELDS)
                
                if "maxResults" not in args_copy:
                    args_copy["maxResults"] = 10
                
                params = {k: v for k, v in args_copy.items() if v is not None}
                resp = await client.get(f"{BASE_URL}/{apiname}", params=params)
                resp.raise_for_status()
                data = resp.json()
                
                if isinstance(data, dict) and "resultsets" in data:
                    filtered_results = []
                    
                    resultsets = data["resultsets"]
                    
                    for item in data["resultsets"]["features"]:
                        filtered_item = {f: item["properties"][f] for f in selected_fields if f in item["properties"]}
                        filtered_results.append(filtered_item)
                    
                    response_data = {
                        "totalCount": data["metadata"]["totalCount"],
                        "result": filtered_results
                    }
                    res_text = json.dumps(response_data, indent=2, ensure_ascii=False)
                    if not fields_provided:
                        res_text += "\n\n(ヒント: 'get_dataset_config' で項目名を確認し、'fields' を指定すると詳細な情報を取得できます)"
                    
                    return [TextContent(type="text", text=res_text)]
                
                return [TextContent(type="text", text=json.dumps(data, indent=2, ensure_ascii=False))]

            else:
                raise ValueError(f"Unknown tool: {name}")

        except Exception as e:
            return [TextContent(type="text", text=f"Error: {str(e)}", isError=True)]

# 4. メイン処理
async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
