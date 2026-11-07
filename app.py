import streamlit as st
import pandas as pd
import plotly.express as px
from langchain_openai import AzureChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Dashboard & Suporte a Obra - COREN SP",
    layout="wide",
    page_icon="🏗️"
)

# --- INICIALIZAÇÃO DA SESSÃO ---
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "qa_chain" not in st.session_state:
    st.session_state.qa_chain = None
if "connected" not in st.session_state:
    st.session_state.connected = False

# --- FUNÇÃO DE CARREGAMENTO DA PLANILHA ---
@st.cache_data
def load_data():
    file_path = "Coren SP - Sede - Adequação dos Subsolos.xlsx"
    df_raw = pd.read_excel(file_path, sheet_name='Sintético c MO MAT', skiprows=2)
    
    df = df_raw.copy()
    df.columns = [
        'Item', 'Codigo', 'Banco', 'Descricao', 'Und', 'Quant', 
        'Valor_Unit', 'Valor_Unit_BDI', 'MO_Unit', 'MAT_Unit', 
        'MO_Total', 'MAT_Total', 'Total', 'Peso_Percent'
    ]
    df = df.iloc[2:].reset_index(drop=True)
    df = df.dropna(subset=['Descricao']).copy()

    num_cols = ['Quant', 'Valor_Unit', 'Valor_Unit_BDI', 'MO_Unit', 'MAT_Unit', 'MO_Total', 'MAT_Total', 'Total', 'Peso_Percent']
    for c in num_cols:
        df[c] = pd.to_numeric(df[c], errors='coerce')

    df['Item'] = df['Item'].astype(str)
    return df

df = load_data()
etapas = df[~df['Item'].str.contains(r'\.')].copy()
itens_detalhados = df[df['MO_Total'].notna() | df['MAT_Total'].notna()].copy()

# --- BARRA LATERAL: AZURE CONFIG ---
with st.sidebar:
    st.header("🔑 Conexão Azure OpenAI")
    azure_api_key = st.text_input("API Key", type="password")
    azure_endpoint = st.text_input("Endpoint (URL)")
    azure_deployment = st.text_input("Deployment / Modelo LLM")
    azure_api_version = st.text_input("Versão da API", value="2024-02-15-preview")
    
    st.divider()
    persona_default = (
        "Você é um engenheiro orçamentista especialista na obra 'Coren SP - Sede - Adequação do Subsolo'. "
        "Responda dúvidas técnicas e financeiras com base estrita nos dados da planilha."
    )
    system_persona = st.text_area("Persona do Assistente", value=persona_default, height=120)

    if st.button("🚀 Conectar IA", type="primary"):
        if not azure_api_key or not azure_endpoint or not azure_deployment:
            st.error("Preencha todas as credenciais da Azure!")
        else:
            try:
                llm = AzureChatOpenAI(
                    azure_deployment=azure_deployment,
                    azure_endpoint=azure_endpoint,
                    api_key=azure_api_key,
                    api_version=azure_api_version,
                    temperature=0.1
                )
                
                resumo_planilha = df[['Item', 'Descricao', 'Und', 'Quant', 'Total', 'Peso_Percent']].to_string()
                full_prompt = f"{system_persona}\n\nDados da Planilha Orçamentária:\n{resumo_planilha}"

                prompt = ChatPromptTemplate.from_messages([
                    ("system", full_prompt),
                    MessagesPlaceholder("chat_history"),
                    ("human", "{input}"),
                ])
                
                st.session_state.qa_chain = prompt | llm
                st.session_state.connected = True
                st.success("Conectado com sucesso!")
            except Exception as e:
                st.error(f"Erro ao conectar: {e}")

# --- ESTILIZAÇÃO CSS ESTILO WHATSAPP PARA A ABA DE CHAT ---
st.markdown("""
<style>
    .whatsapp-chat-box {
        background-color: #efeae2;
        padding: 20px;
        border-radius: 12px;
        border: 1px solid #d1d7db;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        background-image: radial-gradient(#d4dad6 1px, transparent 1px);
        background-size: 20px 20px;
        min-height: 450px;
        max-height: 600px;
        overflow-y: auto;
        margin-bottom: 20px;
    }
    .wa-message-user {
        background-color: #d9fdd3;
        color: #111b21;
        padding: 10px 14px;
        border-radius: 8px 0px 8px 8px;
        max-width: 75%;
        margin-left: auto;
        margin-bottom: 10px;
        box-shadow: 0 1px 0.5px rgba(0,0,0,0.13);
        font-family: sans-serif;
        font-size: 14px;
    }
    .wa-message-bot {
        background-color: #ffffff;
        color: #111b21;
        padding: 10px 14px;
        border-radius: 0px 8px 8px 8px;
        max-width: 75%;
        margin-right: auto;
        margin-bottom: 10px;
        box-shadow: 0 1px 0.5px rgba(0,0,0,0.13);
        font-family: sans-serif;
        font-size: 14px;
    }
</style>
""", unsafe_allow_html=True)

# --- CORPO PRINCIPAL EM ABAS (ESTRUTURA LIMPA E PERFEITA) ---
tab_dash, tab_chat = st.tabs(["📊 Dashboard & Orçamento", "💬 Chat WhatsApp (Tira-Dúvidas)"])

with tab_dash:
    st.title("🏗️ Dashboard Orçamentário - Coren SP (Subsolos)")

    total_geral = etapas['Total'].sum()
    total_mo = itens_detalhados['MO_Total'].sum()
    total_mat = itens_detalhados['MAT_Total'].sum()

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Valor Total da Obra", f"R$ {total_geral:,.2f}")
    m2.metric("Total Mão de Obra", f"R$ {total_mo:,.2f}", f"{(total_mo/total_geral)*100:.1f}%")
    m3.metric("Total Materiais", f"R$ {total_mat:,.2f}", f"{(total_mat/total_geral)*100:.1f}%")
    m4.metric("B.D.I. Aplicado", "27,0%")

    st.divider()

    col_chart1, col_chart2 = st.columns([3, 2])

    with col_chart1:
        st.subheader("📊 Custos por Etapa (Curva ABC)")
        fig_etapas = px.bar(
            etapas.sort_values(by='Total', ascending=True),
            x='Total',
            y='Descricao',
            orientation='h',
            text_auto='.2s',
            color='Total',
            color_continuous_scale='Blues'
        )
        fig_etapas.update_layout(showlegend=False, xaxis_title="Custo (R$)", yaxis_title="")
        st.plotly_chart(fig_etapas, use_container_width=True)

    with col_chart2:
        st.subheader("⚖️ Proporção M.O. vs Material")
        df_prop = pd.DataFrame({
            'Categoria': ['Mão de Obra', 'Material'],
            'Valor': [total_mo, total_mat]
        })
        fig_pie = px.pie(df_prop, values='Valor', names='Categoria', hole=0.4, color_discrete_sequence=['#1f77b4', '#aec7e8'])
        st.plotly_chart(fig_pie, use_container_width=True)

    st.subheader("📋 Planilha Orçamentária Detalhada")
    st.dataframe(
        df[['Item', 'Codigo', 'Banco', 'Descricao', 'Und', 'Quant', 'MO_Total', 'MAT_Total', 'Total', 'Peso_Percent']],
        use_container_width=True,
        hide_index=True
    )

with tab_chat:
    st.markdown("### 💬 Chat Assistente Técnico - Estilo WhatsApp")
    st.markdown("Tire dúvidas sobre quantitativos, materiais, custos e etapas diretamente com a IA conectada à base de dados.")

    # Cabeçalho decorativo estilo WhatsApp Web
    st.markdown("""
        <div style="background-color: #005e54; color: white; padding: 12px 16px; border-radius: 8px 8px 0 0; display: flex; align-items: center; justify-content: space-between; font-family: sans-serif;">
            <div style="font-weight: bold; font-size: 15px;">🟢 Assistente Obra Coren SP (Online)</div>
            <div style="font-size: 12px; opacity: 0.8;">Base de Dados: Coren SP Subsolos</div>
        </div>
    """, unsafe_allow_html=True)

    # Caixa de exibição de mensagens com estilo WhatsApp
    chat_container = st.container()
    with chat_container:
        st.markdown('<div class="whatsapp-chat-box">', unsafe_allow_html=True)
        
        if not st.session_state.chat_history:
            st.markdown('<div class="wa-message-bot">👋 Olá! Como posso ajudar você com a obra do Coren SP hoje? Pergunte sobre pisos, divisórias, engenharia ou custos.</div>', unsafe_allow_html=True)
        
        for msg in st.session_state.chat_history:
            if isinstance(msg, HumanMessage):
                st.markdown(f'<div class="wa-message-user">{msg.content}</div>', unsafe_allow_html=True)
            elif isinstance(msg, AIMessage):
                st.markdown(f'<div class="wa-message-bot">🤖 {msg.content}</div>', unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)

    # Barra de input e botão de limpeza alinhados perfeitamente
    col_in, col_cln = st.columns([6, 1])
    with col_cln:
        if st.button("🧹 Limpar", use_container_width=True):
            st.session_state.chat_history = []
            st.rerun()

    user_input = st.chat_input("Digite sua dúvida sobre a planilha...")
    if user_input:
        if not st.session_state.connected:
            st.warning("⚠️ Por favor, insira as credenciais da Azure na barra lateral e clique em 'Conectar IA' primeiro.")
        else:
            st.session_state.chat_history.append(HumanMessage(content=user_input))
            try:
                response = st.session_state.qa_chain.invoke({
                    "input": user_input,
                    "chat_history": st.session_state.chat_history[:-1]
                })
                ans = response.content if hasattr(response, "content") else str(response)
                st.session_state.chat_history.append(AIMessage(content=ans))
            except Exception as e:
                st.session_state.chat_history.append(AIMessage(content=f"Erro ao processar resposta: {e}"))
            st.rerun()
