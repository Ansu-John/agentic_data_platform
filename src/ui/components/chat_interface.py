from typing import Any

import streamlit as st


class StreamlitChatInterface:
    """Encapsulates rendering loops and interface components for user-agent dialogue streams."""

    @staticmethod
    def render_history(history: list[dict[str, Any]]) -> None:
        """Renders all elements within the execution thread history
        cleanly across UI redraw states."""
        for message in history:
            role = message.get("role", "user")
            content = message.get("content", "")

            with st.chat_message(role):
                st.markdown(content)

                # Check for structural diagnostic payloads to render in metadata drop downs
                if role == "assistant" and message.get("sql"):
                    with st.expander("👁️ Inspected Query Execution Dialect"):
                        st.code(message["sql"], language="sql")

    @staticmethod
    def capture_input() -> None:
        """Captures input events and handles thread dispatch mapping cleanly."""
        user_prompt = st.chat_input("Ask a question about your enterprise data catalog tables:")
        if user_prompt:
            # Append input array records and invoke response execution pipelines
            st.session_state.conversational_history.append({"role": "user", "content": user_prompt})

            # Instantly redraw parent UI thread for responsive layout execution
            st.rerun()

