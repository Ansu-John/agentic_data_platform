import json

import pandas as pd
import streamlit as st
import structlog

logger = structlog.get_logger()

class EnterpriseDataVisualizer:
    """Dynamically parses and translates raw API query
    result sets into interactive UI dataframes."""

    @staticmethod
    def render_payload(raw_json_str: str | None) -> None:
        """Evaluates schema shapes to generate clean, readable data visualizations."""
        if not raw_json_str:
            return

        try:
            # Safely transform tabular payloads back to relational execution sets
            data_records = json.loads(raw_json_str)
            if not data_records:
                st.info("Query completed successfully, but returned 0 rows matching the request "
                        "filters.")
                return

            df = pd.DataFrame(data_records)

            st.markdown("### 📋 Retrieved Dataset Records")

            # Display interactive enterprise data table with strict search/filter sorting rules
            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True
            )

            # Simple metadata utility layer metrics displaying scale summary footprints
            col1, col2 = st.columns(2)
            with col1:
                st.metric(label="Total Record Count Transferred", value=len(df))
            with col2:
                st.metric(label="Attribute Dimensionality Width", value=len(df.columns))

        except json.JSONDecodeError as e:
            logger.error("payload_deserialization_failed", error=str(e))
            st.error("Visualization Processing Error: Unable to properly parse query data "
                     "structure shapes.")
        except Exception as e:
            logger.error("visualizer_rendering_crash", error=str(e))
            st.error(f"Failed to generate visualization interface layouts: {str(e)}")
