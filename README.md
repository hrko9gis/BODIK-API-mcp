# BODIK API MCPサーバー

BODIK APIを利用して、自治体オープンデータを検索できるMCP（Model Context Protocol）サーバーです。

## 機能

- 条件を設定したデータの検索、取得

## 利用可能なツール
#### 1. list_apinames

利用可能なAPI名一覧を取得

#### 2. list_organizations

特定データセットを提供する自治体一覧を取得

#### 3. list_all_organizations

全自治体一覧を取得

#### 4. get_config

データセット構成情報の取得

#### 5. search_get

GET検索

#### 6. search_post

POST検索（高度検索）

#### 7. search_get_records

GET検索結果からpropertiesのみ抽出

#### 8. search_get_csv

GET検索結果をCSV形式で返す

#### 9. search_get_geojson

GET検索結果をGeoJSON形式で返す

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
            ],
            "env": {
              "BODIK_API_BASE": "https://wapi.bodik.jp"
            }
        }
    }
}
```

3. MCPのサーバーURLに http://localhost:3000 を入力します

4. 保存します

5. 接続します

## ライセンス

MIT

## 謝辞

このプロジェクトは、ビッグデータ＆オープンデータ・イニシアティブ九州（BODIK事業）のAPIを利用しています。APIの提供に感謝いたします。
