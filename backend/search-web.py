import os
import json
from tavily import TavilyClient

def lambda_handler(event, context):
    # 環境変数からAPIキーを取得
    tavily_api_key = os.environ.get('TAVILY_API_KEY')
    
    # eventからクエリパラメータを取得
    parameters = event.get('parameters', [])
    for param in parameters:
        if param.get('name') == 'query':
            query = param.get('value')
            break
    
    # Tavilyクライアントを初期化して検索を実行
    client = TavilyClient(api_key=tavily_api_key)
    
    # より詳細な検索を実行（日本語コンテンツの精度向上のため）
    try:
        # search()メソッドを使用してより詳細な結果を取得
        search_response = client.search(
            query=query,
            search_depth="advanced",  # より深い検索
            max_results=10,
            include_answer=True,      # AI生成の回答を含める
            include_raw_content=False, # 生のHTMLは除外（容量削減）
            include_images=False,     # 画像検索は除外
            chunks_per_source=2       # 各ソースから2つのチャンクを取得
        )
        
        # 検索結果を整形
        search_result = {
            "query": query,
            "answer": search_response.get("answer", ""),
            "results": []
        }
        
        # 各結果を整形
        for result in search_response.get("results", []):
            search_result["results"].append({
                "title": result.get("title", ""),
                "url": result.get("url", ""),
                "content": result.get("content", ""),
                "score": result.get("score", 0)
            })
        
        # コンテキスト形式のテキストも生成
        context_parts = []
        if search_result["answer"]:
            context_parts.append(f"【AI回答】\n{search_result['answer']}\n")
        
        context_parts.append("【検索結果】")
        for idx, result in enumerate(search_result["results"], 1):
            context_parts.append(f"\n{idx}. {result['title']}")
            context_parts.append(f"   URL: {result['url']}")
            context_parts.append(f"   {result['content'][:200]}...")
        
        search_result["context"] = "\n".join(context_parts)
        
    except Exception as e:
        # エラーが発生した場合は、元のget_search_contextメソッドを使用
        print(f"Search error: {str(e)}, falling back to get_search_context")
        search_result = client.get_search_context(
            query=query,
            search_depth="advanced",
            max_results=10
        )
    
    # 成功レスポンスを返す
    return {
        'messageVersion': event['messageVersion'],
        'response': {
            'actionGroup': event['actionGroup'],
            'function': event['function'],
            'functionResponse': {
                'responseBody': {
                    'TEXT': {
                        'body': json.dumps(search_result, ensure_ascii=False)
                    }
                }
            }
        }
    }
