import requests
import streamlit as st
from src.ui.config.settings import ui_settings

st.set_page_config(
    page_title=ui_settings.application_title,
    layout=ui_settings.page_layout
)

st.title("📊 Governance Driven Insights Explorer")
st.markdown("---")

# Session state array allocations for conversational thread patterns
if "conversational_history" not in st.session_state:
    st.session_state.conversational_history = []

# Output the running chat record across UI redraw iterations
for dialog in st.session_state.conversational_history:
    with st.chat_message(dialog["role"]):
        st.markdown(dialog["content"])
        if dialog.get("sql"):
            with st.expander("Inspected SQL Dialect"):
                st.code(dialog["sql"], language="sql")

# Inbound customer stream capture interface point
if inbound_prompt := st.chat_input("Ask a question about your enterprise catalog:"):
    st.session_state.conversational_history.append({"role": "user", "content": inbound_prompt})
    with st.chat_message("user"):
        st.markdown(inbound_prompt)

    with st.chat_message("assistant"), st.spinner("Executing secure analytical agent loop..."):
        try:
            target_endpoint = f"{ui_settings.api_gateway_endpoint}/ask"
            api_payload = {"query": inbound_prompt}

            network_response = requests.post(
                url=target_endpoint,
                json=api_payload,
                timeout=120 # Account for cold-start Bedrock token streaming generation latencies
            )
            network_response.raise_for_status()
            payload_data = network_response.json()

            business_answer = payload_data.get("answer", "No context returned.")
            query_sql = payload_data.get("generated_sql")

            st.markdown(business_answer)
            if query_sql:
                with st.expander("Inspected SQL Dialect"):
                    st.code(query_sql, language="sql")

            st.session_state.conversational_history.append({
                "role": "assistant",
                "content": business_answer,
                "sql": query_sql
            })

        except requests.exceptions.RequestException as error:
            st.error(f"Network interface transaction degradation: {str(error)}")
