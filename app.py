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
    system_persona = st.text_area("Persona do Assistente", value=persona_default, height=100)

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

# --- CORPO PRINCIPAL: DASHBOARD ---
st.title("📊 Painel Analítico de Custos da Obra")
st.caption("Obra: Coren SP - Sede - Adequação do Subsolo")

total_geral = etapas['Total'].sum()
total_mo = itens_detalhados['MO_Total'].sum()
total_mat = itens_detalhados['MAT_Total'].sum()

m1, m2, m3, m4 = st.columns(4)
m1.metric("Total da Obra", f"R$ {total_geral:,.2f}")
m2.metric("Mão de Obra", f"R$ {total_mo:,.2f}", f"{(total_mo/total_geral)*100:.1f}%")
m3.metric("Materiais", f"R$ {total_mat:,.2f}", f"{(total_mat/total_geral)*100:.1f}%")
m4.metric("B.D.I.", "27,0%")

st.divider()

col_chart1, col_chart2 = st.columns([3, 2])

with col_chart1:
    st.subheader("Custo Total por Etapa (R$)")
    fig_etapas = px.bar(
        etapas.sort_values(by='Total', ascending=True),
        x='Total',
        y='Descricao',
        orientation='h',
        text_auto='.2s',
        color='Total',
        color_continuous_scale='Purples'
    )
    fig_etapas.update_layout(showlegend=False, xaxis_title="", yaxis_title="")
    st.plotly_chart(fig_etapas, use_container_width=True)

with col_chart2:
    st.subheader("Distribuição de Valores")
    df_prop = pd.DataFrame({
        'Categoria': ['Mão de Obra', 'Material'],
        'Valor': [total_mo, total_mat]
    })
    fig_pie = px.pie(df_prop, values='Valor', names='Categoria', hole=0.5, color_discrete_sequence=['#4B0082', '#00FA9A'])
    st.plotly_chart(fig_pie, use_container_width=True)

st.subheader("📋 Planilha Orçamentária")
st.dataframe(
    df[['Item', 'Codigo', 'Banco', 'Descricao', 'Und', 'Quant', 'MO_Total', 'MAT_Total', 'Total', 'Peso_Percent']],
    use_container_width=True,
    hide_index=True
)

# --- CSS CORRIGIDO PARA GARANTIR VISIBILIDADE TOTAL DOS TEXTOS E BALÕES ---
st.markdown("""
<style>
    /* Card flutuante fixado no canto inferior direito */
    [data-testid="stVerticalBlock"] > div:has(div.floating-chat-marker) {
        position: fixed !important;
        bottom: 30px !important;
        right: 30px !important;
        width: 390px !important;
        max-height: 600px !important;
        background-color: #111b21 !important;
        border-radius: 16px !important;
        box-shadow: 0px 8px 32px rgba(0, 0, 0, 0.6) !important;
        z-index: 999999 !important;
        padding: 16px !important;
        border: 1px solid #222d34 !important;
        overflow: hidden !important;
    }

    /* Força cor branca para todo texto dentro do chat flutuante */
    [data-testid="stVerticalBlock"] > div:has(div.floating-chat-marker) p, 
    [data-testid="stVerticalBlock"] > div:has(div.floating-chat-marker) span, 
    [data-testid="stVerticalBlock"] > div:has(div.floating-chat-marker) label {
        color: #e9edef !important;
    }

    /* Estilização correta das mensagens de chat */
    [data-testid="stVerticalBlock"] > div:has(div.floating-chat-marker) [data-testid="stChatMessage"] {
        padding: 8px 12px !important;
        margin-bottom: 8px !important;
        border-radius: 10px !important;
    }

    /* Mensagem do Usuário (Verde WhatsApp Escuro) */
    [data-testid="stVerticalBlock"] > div:has(div.floating-chat-marker) [data-testid="stChatMessage"]:nth-of-type(even) {
        background-color: #005c4b !important;
    }

    /* Mensagem do Bot (Cinza Escuro) */
    [data-testid="stVerticalBlock"] > div:has(div.floating-chat-marker) [data-testid="stChatMessage"]:nth-of-type(odd) {
        background-color: #202c33 !important;
    }
</style>
""", unsafe_allow_html=True)

# --- WIDGET DO CHAT FLUTUANTE DA DIREITA ---
with st.container():
    st.markdown('<div class="floating-chat-marker"></div>', unsafe_allow_html=True)
    
    # Cabeçalho do Card Flutuante
    st.markdown("""
        <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 12px; border-bottom: 1px solid #222d34; padding-bottom: 8px;">
            <div style="font-size: 24px;">🎧</div>
            <div>
                <div style="font-weight: bold; color: #ffffff; font-size: 15px;">Suporte de Obra Online</div>
                <div style="font-size: 11px; color: #00ff88;">● online agora</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Caixa com rolagem para as mensagens
    chat_box = st.container(height=300)
    with chat_box:
        if not st.session_state.chat_history:
            st.chat_message("assistant").write("Olá! Como posso ajudar você hoje com as dúvidas da planilha?")

        for msg in st.session_state.chat_history:
            if isinstance(msg, HumanMessage):
                st.chat_message("user").write(msg.content)
            elif isinstance(msg, AIMessage):
                st.chat_message("assistant").write(msg.content)

    # Caixa de entrada e botão de envio
    with st.form("chat_form", clear_on_submit=True):
        user_input = st.text_input("Digite sua dúvida...", label_visibility="collapsed", placeholder="Digite sua dúvida...")
        submit_button = st.form_submit_button("Enviar 🚀", use_container_width=True)

        if submit_button and user_input:
            if not st.session_state.connected:
                st.error("Conecte a Azure na barra lateral primeiro!")
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
                    st.session_state.chat_history.append(AIMessage(content=f"Erro: {e}"))
                st.rerun()
