import asyncio
import httpx
import json
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.types import Tool, TextContent
from typing import Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 1. サーバーの初期化
app = FastAPI()

# CORS設定を追加（ブラウザや外部からの接続を許可）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

server = Server("BODIK-API-mcp")

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
                
                # キー「fields」を削除して軽量化
                if isinstance(data, dict):
                    data.pop("fields", None)   # fieldsを削除
                    data.pop("mapping", None)  # mappingを削除

                logger.info(f"get_dataset_config: {data}")
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
                # telNumber を telephoneNumber に修正（または両方含める）
                selected_fields = args_copy.pop("fields", ["name", "address", "telephoneNumber", "lat", "lon"])
                
                if "maxResults" not in args_copy:
                    args_copy["maxResults"] = 10
                
                params = {k: v for k, v in args_copy.items() if v is not None}
                resp = await client.get(f"{BASE_URL}/{apiname}", params=params)
                resp.raise_for_status()
                data = resp.json()

                # --- 修正のポイント: レスポンスをリストに正規化する ---
                results = []
                total_count = 0

                if isinstance(data, list):
                    results = data
                    total_count = len(data)
                elif isinstance(data, dict):
                    # "result"キーがある場合、または辞書自体が1件のデータの場合に対応
                    results = data.get("result", [data] if "apiname" not in data else [])
                    total_count = data.get("totalCount", len(results))
                
                # フィルタリング処理の実行
                filtered_results = []
                for item in results:
                    # 指定されたフィールドが存在する場合のみ抽出
                    filtered_item = {f: item.get(f) for f in selected_fields if f in item}
                    # 全くマッチしなかった項目を避けるため、空でない場合のみ追加
                    if filtered_item:
                        filtered_results.append(filtered_item)
                    else:
                        # フィルターが1つもマッチしない場合は元の項目を出す（デバッグ・利便性のため）
                        filtered_results.append(item)

                response_data = {
                    "totalCount": total_count,
                    "result": filtered_results
                }
                
                res_text = json.dumps(response_data, indent=2, ensure_ascii=False)
                if not fields_provided:
                    res_text += "\n\n(ヒント: 'get_dataset_config' で項目名を確認し、'fields' を指定すると詳細な情報を取得できます)"
                
                logger.info(f"search_dataset filtered: {len(filtered_results)} items")
                return [TextContent(type="text", text=res_text)]

            else:
                raise ValueError(f"Unknown tool: {name}")

        except Exception as e:
            return [TextContent(type="text", text=f"Error: {str(e)}", isError=True)]

# SSEの設定
sse = SseServerTransport("/api/index/messages")

@app.get("/api/index/sse")
async def handle_sse(request: Request):
    scope = request.scope
    receive = scope.get("receive")
    send = scope.get("send")
    
    # 修正ポイント: 'as mcp_scope' ではなく '(read_stream, write_stream)' で直接受け取る
    async with sse.connect_sse(scope, receive, send) as (read_stream, write_stream):
        await server.run(
            read_stream,  # .read_stream は不要になりました
            write_stream, # .write_stream は不要になりました
            server.create_initialization_options()
        )

@app.post("/api/index/messages")
async def handle_messages(request: Request):
    scope = request.scope
    receive = scope.get("receive")
    send = scope.get("send")
    
    await sse.handle_post_request(scope, receive, send)