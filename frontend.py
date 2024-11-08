# 必要なPythonライブラリをインポート
import uuid, boto3
import streamlit as st

# Bedrockクライアントを作成
if "client" not in st.session_state:
    st.session_state.client = boto3.client("bedrock-agent-runtime")
client = st.session_state.client

# セッションIDを作成
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
session_id = st.session_state.session_id

# メッセージ格納用のリストを作成
if "messages" not in st.session_state:
    st.session_state.messages = []
messages = st.session_state.messages

# タイトルを表示
st.title("パワポ作ってメールで送るマン")

# 過去のメッセージを表示
for message in messages:
    with st.chat_message(message['role']):
        st.markdown(message['text'])

# チャット入力欄を定義
if prompt := st.chat_input("例：ナポレオンの生涯を資料にまとめて"):

    # ユーザーの入力をメッセージに追加
    messages.append({"role": "human", "text": prompt})

    # ユーザーの入力を画面に表示
    with st.chat_message("user"):
        st.markdown(prompt)

    # Bedrockエージェントの呼び出し設定
    response = client.invoke_agent(
        agentId="SUMBIJL3GH", # エージェントID
        agentAliasId="XMS4OCD5UF", # エージェントエイリアスID
        sessionId=session_id,
        enableTrace=True,
        inputText=prompt,
    )

    # エージェントの回答を画面に表示
    with st.chat_message("assistant"):
        for event in response.get("completion"):

            # トレースイベントが更新されたら画面に表示
            if "trace" in event:
                if "orchestrationTrace" in event["trace"]["trace"]:
                    orchestrationTrace = event["trace"]["trace"]["orchestrationTrace"]

                    if "modelInvocationInput" in orchestrationTrace:
                        with st.expander("思考中…", expanded=False):
                            st.write(orchestrationTrace)

                    if "rationale" in orchestrationTrace:
                        with st.expander("次のアクションを決定しました", expanded=False):
                            st.write(orchestrationTrace)

                    if "invocationInput" in orchestrationTrace:
                        with st.expander("次のタスクへのインプットを生成しました", expanded=False):
                            st.write(orchestrationTrace)

                    if "observation" in orchestrationTrace:
                        with st.expander("タスクの結果から洞察を得ています…", expanded=False):
                            st.write(orchestrationTrace)

            # エージェントの回答が出力されたら画面に表示
            if "chunk" in event:
                chunk = event["chunk"]
                answer = chunk["bytes"].decode()

                st.write(answer)
                messages.append({"role": "assistant", "text": answer})