import json
import uuid
import boto3
import streamlit as st
from botocore.exceptions import ClientError
from botocore.eventstream import EventStreamError

def initialize_session():
    """セッションの初期設定を行う"""
    if "client" not in st.session_state:
        # Streamlit Cloud用にAWS認証情報を設定
        if "AWS_ACCESS_KEY_ID" in st.secrets:
            st.session_state.client = boto3.client(
                "bedrock-agent-runtime",
                region_name=st.secrets.get("AWS_DEFAULT_REGION"),
                aws_access_key_id=st.secrets["AWS_ACCESS_KEY_ID"],
                aws_secret_access_key=st.secrets["AWS_SECRET_ACCESS_KEY"]
            )
        else:
            # ローカル開発用（環境変数またはデフォルト認証を使用）
            st.session_state.client = boto3.client("bedrock-agent-runtime")
    
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())
    
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    if "last_prompt" not in st.session_state:
        st.session_state.last_prompt = None
    
    if "agent_id" not in st.session_state:
        st.session_state.agent_id = st.secrets.get("AGENT_ID", "")
    
    if "agent_alias_id" not in st.session_state:
        st.session_state.agent_alias_id = st.secrets.get("AGENT_ALIAS_ID", "")
    
    return st.session_state.client, st.session_state.session_id, st.session_state.messages

def display_chat_history(messages):
    """チャット履歴を表示する"""
    st.title("パワポ作ってメールで送るマン")
    st.text("ｴｯﾎｴｯﾎ　あなたの代わりにスライド作らなきゃ　ｴｯﾎｴｯﾎ")
    
    for message in messages:
        with st.chat_message(message['role']):
            st.markdown(message['text'])

def handle_trace_event(event):
    """トレースイベントの処理を行う"""
    if "orchestrationTrace" not in event["trace"]["trace"]:
        return
    
    trace = event["trace"]["trace"]["orchestrationTrace"]
    
    # 「モデル入力」トレースの表示
    if "modelInvocationInput" in trace:
        with st.expander("🤔 思考中…", expanded=False):
            input_trace = trace["modelInvocationInput"]["text"]
            try:
                st.json(json.loads(input_trace))
            except:
                st.write(input_trace)
    
    # 「モデル出力」トレースの表示
    if "modelInvocationOutput" in trace:
        output_trace = trace["modelInvocationOutput"]["rawResponse"]["content"]
        with st.expander("💡 思考がまとまりました", expanded=False):
            try:
                thinking = json.loads(output_trace)["content"][0]["text"]
                if thinking:
                    st.write(thinking)
                else:
                    st.write(json.loads(output_trace)["content"][0])
            except:
                st.write(output_trace)
    
    # 「根拠」トレースの表示
    if "rationale" in trace:
        with st.expander("✅ 次のアクションを決定しました", expanded=True):
            st.write(trace["rationale"]["text"])
    
    # 「ツール呼び出し」トレースの表示
    if "invocationInput" in trace:
        invocation_type = trace["invocationInput"]["invocationType"]
                
        if invocation_type == "ACTION_GROUP":
            with st.expander("💻 Lambdaを実行中…", expanded=False):
                st.write(trace['invocationInput']['actionGroupInvocationInput'])
    
    # 「観察」トレースの表示
    if "observation" in trace:
        obs_type = trace["observation"]["type"]
        
        if obs_type == "ACTION_GROUP":
            with st.expander(f"💻 Lambdaの実行結果を取得しました", expanded=False):
                st.write(trace["observation"]["actionGroupInvocationOutput"]["text"])
                
def invoke_bedrock_agent(client, session_id, prompt, agent_id, agent_alias_id):
    """Bedrockエージェントを呼び出す"""
    return client.invoke_agent(
        agentId=agent_id,
        agentAliasId=agent_alias_id,
        sessionId=session_id,
        enableTrace=True,
        inputText=prompt,
    )

def handle_agent_response(response, messages):
    """エージェントのレスポンスを処理する"""
    with st.chat_message("assistant"):
        for event in response.get("completion"):
            if "trace" in event:
                handle_trace_event(event)
            
            if "chunk" in event:
                answer = event["chunk"]["bytes"].decode()
                st.write(answer)
                messages.append({"role": "assistant", "text": answer})

def show_error_popup(exeption):
    """エラーポップアップを表示する"""
    if exeption == "throttlingException":
        error_message = "【エラー】Bedrockのモデル負荷が高いようです。1分ほど待ってから、ブラウザをリロードして再度お試しください🙏（改善しない場合は、モデルを変更するか[サービスクォータの引き上げ申請](https://aws.amazon.com/jp/blogs/news/generative-ai-amazon-bedrock-handling-quota-problems/)を実施ください）"
    st.error(error_message)

def main():
    """メインのアプリケーション処理"""
    # ページ設定でサイドバーを初期状態で閉じる
    st.set_page_config(
        page_title="パワポ作ってメールで送るマン",
        page_icon="📧",
        initial_sidebar_state="collapsed"
    )
    
    client, session_id, messages = initialize_session()
    
    # サイドバーでAgent IDとAlias IDを入力
    with st.sidebar:
        st.header("設定")
        agent_id = st.text_input(
            "エージェントID",
            value=st.session_state.agent_id
        )
        agent_alias_id = st.text_input(
            "エイリアスID",
            value=st.session_state.agent_alias_id
        )
        
        # 入力値をセッションに保存
        st.session_state.agent_id = agent_id
        st.session_state.agent_alias_id = agent_alias_id
    
    display_chat_history(messages)
    
    # Agent IDが設定されていない場合はチャット入力を無効化
    if not agent_id or not agent_alias_id:
        st.chat_input("例：日本のBedrock最新事例をリサーチして", disabled=True)
        return
    
    if prompt := st.chat_input("例：日本のBedrock最新事例をリサーチして"):
        messages.append({"role": "human", "text": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        try:
            response = invoke_bedrock_agent(client, session_id, prompt, agent_id, agent_alias_id)
            handle_agent_response(response, messages)
            
        except (EventStreamError, ClientError) as e:
            if "throttlingException" in str(e):
                show_error_popup("throttlingException")
            else:
                raise e

if __name__ == "__main__":
    main()
