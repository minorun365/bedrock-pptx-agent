# 必要なPythonライブラリをインポート
import os, json, boto3

# 環境変数からSNSトピックARNを取得
SNS_TOPIC_ARN = os.environ.get("SNS_TOPIC_ARN")

# Lambdaのメイン関数
def lambda_handler(event, context):

    # イベントパラメーターからURLを取得
    signed_url = event.get("parameters", [{}])[0].get("value")

    # SNSメッセージの発行
    boto3.client("sns").publish(
        TopicArn=SNS_TOPIC_ARN, 
        Message=f"Bedrockエージェントがスライドを作成しました。URLの有効期限は1時間です：\n{signed_url}",
        Subject="スライド作成通知"
    )

    # エージェント用のレスポンスを返す
    return {
        "messageVersion": "1.0",
        "response": {
            "actionGroup": event.get("actionGroup", "send-email"),
            "function": event.get("function", "send-email"),
            "functionResponse": {
                "responseBody": {
                    "TEXT": {
                        "body": json.dumps(
                            {
                                "message": "Email sent successfully",
                                "presentationUrl": signed_url,
                            }
                        )
                    }
                }
            },
        },
    }