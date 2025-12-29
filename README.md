# BODIK API MCPサーバー

ビッグデータ＆オープンデータ・イニシアティブ九州（BODIK事業）が提供する「自治体標準オープンデータセット」のデータを生成AIから BODIK API 経由で安全かつ柔軟に利用できるようにする MCPサーバーです。

## 特徴

- 動的なデータセット取得: BODIKが提供する最新のAPI一覧をリアルタイムに取得します。
- 柔軟な検索: 緯度経度による周辺検索、自治体名や施設名による絞り込みに対応しています。
- 構造把握: 各データセットのフィールド定義（config）を確認できるため、AIがデータの構造を正しく理解できます。

## 利用可能なツール
#### 1. get_api_list

利用可能なデータセット（apiname）の一覧を取得します。

#### 2. get_all_organizations

データを提供している全自治体と自治体コードの一覧を取得します。

#### 3. get_dataset_config

指定したデータセットのフィールド定義や型情報を確認します。

#### 4. get_organization

特定のデータセットを提供している自治体一覧を取得します。

#### 5. search_dataset

指定したデータセットを各種パラメータで検索します。


## Claude Desktop での使用

Claude Desktop でMCPサーバーを追加して利用することができます。
下記手順ではC:\workにソースコードを配置して利用する前提で説明していますが、ご利用の環境に合わせて配置場所を変更してもらってかまいません。

1. Node.js (npx) のインストール
Claude Desktop とリモートサーバーを接続するツールを動かすために必要です。​
公式サイトからダウンロード: 公式サイト（https://nodejs.org/）にアクセスし、「LTS（推奨版）」をダウンロードします。​
推奨版をインストール: ダウンロードしたファイルを実行します。インストーラーの指示に従って完了させます。

2. Python のインストール
公式サイトからダウンロード: 公式サイト（https://www.python.org/downloads/）にアクセスし、最新版 をダウンロードします。​
最新版をインストール: ダウンロードしたファイルを実行します。インストーラーの指示に従って完了させます。インストール画面の最初に出てくる 「Add Python to PATH」 というチェックボックスに必ずチェックを入れてください。​

3. 依存ライブラリのインストール

　　　pip install mcp httpx

4. MCP サーバーのファイルをダウンロード​
MCP サーバーのコードをダウンロード: 下記URLにアクセスします。​
　https://github.com/hrko9gis/BODIK-API-mcp/blob/main/BODIK-API-mcp.py​
ダウンロード: 「Download raw file」をクリックしてコードをダウンロードします。

5. ファイルの配置: ダウンロードしたファイルを下記に配置します。work フォルダがない場合は作成します。​

　 　C:\work

6. Claude Desktopへの登録
claude_desktop_config.json（通常は以下のパスにあります）を開き、サーバーの設定を追加します。

　　Windows: %APPDATA%\Interactions\claude_desktop_config.json

　　macOS: ~/Library/Application Support/Claude/claude_desktop_config.json

```json
{​
  "mcpServers": {​
    "BODIK-API-mcp": {​
      "command": "python",​
      "args": [​
        "-u",​
        "C:\\work\\BODIK-API-mcp.py"​
      ]​
    }​
  }
}
```

## ライセンス

BODIK APIの利用条件および各データ提供元のライセンスに従ってください。

## 謝辞

ビッグデータ＆オープンデータ・イニシアティブ九州（BODIK事業）のBODIK APIを利用しています。APIの提供に感謝いたします。

## 参考資料

* BODIK API Manual
* [https://www.bodik.jp/project/bodik-api/bodik-api-manual/](https://www.bodik.jp/project/bodik-api/bodik-api-manual/)
