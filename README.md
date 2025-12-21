# BODIK API MCPサーバー

BODIK API（自治体オープンデータカタログ）を **Model Context Protocol（MCP）** 経由で生成AIから安全かつ柔軟に利用できるようにする MCPサーバーです。

## 機能

- 条件を設定したデータの検索、取得

## 利用可能なツール
#### 1. list_apinames

利用可能なBODIKデータセットAPI名一覧を取得する

#### 2. list_organizations

データを公開している組織の一覧を取得する

#### 3. list_all_organizations

BODIKに公開しているすべての組織の一覧を取得する

#### 4. get_config

データセット設定情報を取得する

#### 5. search_get

GETで検索してデータセットを取得する

#### 6. search_post

POSTで検索してデータセットを取得する

#### 7. search_get_records

属性情報のみ抽出して取得する

#### 8. search_get_csv

CSV形式でデータを取得する

#### 9. search_get_geojson

GeoJSON形式でデータを取得する

## Claude Desktop での使用

Claude Desktop でMCPサーバーを追加して利用することができます。

1. Claude Desktop で設定画面を開きます

2. このMCPサーバーを追加します
```json
{
    "mcpServers": {
        "BODIK-API-mcp": {
            "command": "/Users/***/.local/bin/uv",
            "args": [
                "--directory",
                "＜BODIK-API-mcp.pyが存在するディレクトリを絶対パスで指定＞"
                "run",
                "BODIK-API-mcp.py"
            ]
        }
    }
}
```

3. 保存します

## ライセンス

BODIK APIの利用条件および各データ提供元のライセンスに従ってください。

## 謝辞

ビッグデータ＆オープンデータ・イニシアティブ九州（BODIK事業）のBODIK APIを利用しています。APIの提供に感謝いたします。

## 参考資料

* BODIK API Manual
* [https://www.bodik.jp/project/bodik-api/bodik-api-manual/](https://www.bodik.jp/project/bodik-api/bodik-api-manual/)
* API Viewer: [https://wapi.bodik.jp/apiviewer](https://wapi.bodik.jp/apiviewer)
* API Search: [https://wapi.bodik.jp/apisearch](https://wapi.bodik.jp/apisearch)

