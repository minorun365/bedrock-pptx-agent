import uuid
import boto3
import json
import streamlit as st
from dotenv import load_dotenv

def initialize_session():
    """セッションの初期設定を行う"""
    if "client" not in st.session_state:
        st.session_state.client = boto3.client("bedrock-agent-runtime", region_name="us-east-1")
    
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())
    
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    return st.session_state.client, st.session_state.session_id, st.session_state.messages

def display_chat_history(messages):
    """チャット履歴を表示する"""
    st.title("パワポ作ってメールで送るマン")
    
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
        
        if invocation_type == "AGENT_COLLABORATOR":
            agent_name = trace["invocationInput"]["agentCollaboratorInvocationInput"]["agentCollaboratorName"]
            with st.expander(f"🤖 サブエージェント「{agent_name}」を呼び出し中…", expanded=True):
                st.write(trace["invocationInput"]["agentCollaboratorInvocationInput"]["input"]["text"])
        
        elif invocation_type == "KNOWLEDGE_BASE":
            with st.expander("📖 ナレッジベースを検索中…", expanded=False):
                st.write(trace["invocationInput"]["knowledgeBaseLookupInput"]["text"])
        
        elif invocation_type == "ACTION_GROUP":
            with st.expander("💻 Lambdaを実行中…", expanded=False):
                st.write(trace['invocationInput']['actionGroupInvocationInput'])
    
    # 「観察」トレースの表示
    if "observation" in trace:
        obs_type = trace["observation"]["type"]
        
        if obs_type == "KNOWLEDGE_BASE":
            with st.expander("🔍 ナレッジベースから検索結果を取得しました", expanded=False):
                st.write(trace["observation"]["knowledgeBaseLookupOutput"]["retrievedReferences"])
        
        elif obs_type == "AGENT_COLLABORATOR":
            agent_name = trace["observation"]["agentCollaboratorInvocationOutput"]["agentCollaboratorName"]
            with st.expander(f"🤖 サブエージェント「{agent_name}」から回答を取得しました", expanded=True):
                st.write(trace["observation"]["agentCollaboratorInvocationOutput"]["output"]["text"])

def main():
    """メインのアプリケーション処理"""
    client, session_id, messages = initialize_session()
    display_chat_history(messages)
    
    if prompt := st.chat_input("例：ナポレオンの生涯を資料にまとめて"):
        # ユーザー入力の処理
        messages.append({"role": "human", "text": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Bedrockエージェントの呼び出し
        load_dotenv()
        response = client.invoke_agent(
            agentId=os.getenv("AGENT_ID"),
            agentAliasId=os.getenv("AGENT_ALIAS_ID"),
            sessionId=session_id,
            enableTrace=True,
            inputText=prompt,
        )
        
        # レスポンスの処理
        with st.chat_message("assistant"):
            for event in response.get("completion"):
                if "trace" in event:
                    handle_trace_event(event)
                
                if "chunk" in event:
                    answer = event["chunk"]["bytes"].decode()
                    st.write(answer)
                    messages.append({"role": "assistant", "text": answer})

if __name__ == "__main__":
    main()