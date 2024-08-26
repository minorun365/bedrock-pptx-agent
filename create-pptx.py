import os, json, boto3
from pptx import Presentation
from datetime import datetime

S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")


def lambda_handler(event, context):
    topic = next(
        (item["value"] for item in event["parameters"] if item["name"] == "topic"), ""
    )
    content = next(
        (item["value"] for item in event["parameters"] if item["name"] == "content"), ""
    )

    # contentの先頭と末尾の空白文字を削除
    content = content.strip()

    # コンテンツを複数のスライドに分割
    slides_content = content.split("\n\n")
    prs = Presentation()

    # タイトルスライド
    title_slide_layout = prs.slide_layouts[0]
    slide = prs.slides.add_slide(title_slide_layout)
    title = slide.shapes.title
    subtitle = slide.placeholders[1]
    title.text = topic
    subtitle.text = f"作成日: {datetime.now().strftime('%Y年%m月%d日')}"

    # コンテンツスライド
    for i, slide_content in enumerate(slides_content):
        content_slide_layout = prs.slide_layouts[1]  # テキストとタイトルのレイアウト
        slide = prs.slides.add_slide(content_slide_layout)
        title = slide.shapes.title
        content_shape = slide.placeholders[1]

        lines = slide_content.split("\n")
        if lines:
            # 最初の行を見出しとして使用（行頭の箇条書き記号を削除）
            title.text = lines[0].lstrip("- ")
            # 残りの行を本文として使用（行頭の"- "を削除）
            content_shape.text = "\n".join([line.lstrip("- ") for line in lines[1:]])
        else:
            title.text = "詳細"
            content_shape.text = slide_content

    # S3にファイルを保存
    s3 = boto3.client("s3")
    bucket_name = S3_BUCKET_NAME
    file_name = f"{topic.replace(' ', '_')}.pptx"
    file_path = f"/tmp/{file_name}"
    prs.save(file_path)
    s3.upload_file(file_path, bucket_name, file_name)

    # 署名付きURLを生成
    url = s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket_name, "Key": file_name},
        ExpiresIn=3600,  # URLの有効期限を1時間に設定
    )

    return {
        "messageVersion": "1.0",
        "response": {
            "actionGroup": event["actionGroup"],
            "function": event["function"],
            "functionResponse": {
                "responseBody": {"TEXT": {"body": json.dumps({"signed_url": url})}}
            },
        },
    }
