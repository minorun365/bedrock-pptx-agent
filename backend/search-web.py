# 必要なPythonライブラリをインポート
import json
from duckduckgo_search import DDGS

# メインのLambda関数
def lambda_handler(event, context):

    # イベントパラメーターから検索クエリを取得
    query = next(
        (item["value"] for item in event["parameters"] if item["name"] == "query"), ""
    )

    # DuckDuckGoを使用して検索を実行
    results = list(
        DDGS().text(keywords=query, region="jp-jp", safesearch="off", timelimit=None, max_results=10)
    )

    # 検索結果をフォーマット
    summary = "\n\n".join(
        [f"タイトル: {result['title']}\n要約: {result['body']}" for result in results]
    )

    # エージェント用のレスポンスを返す
    return {
        "messageVersion": "1.0",
        "response": {
            "actionGroup": event["actionGroup"],
            "function": event["function"],
            "functionResponse": {
                "responseBody": {
                    "TEXT": {
                        "body": json.dumps({"summary": summary}, ensure_ascii=False)
                    }
                }
            },
        },
    }