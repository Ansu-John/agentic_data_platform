import os
from typing import Any

import awswrangler as wr
import boto3
import pandas as pd
import streamlit as st
from botocore.exceptions import ClientError

# --- Configuration & Environment Variables ---
st.set_page_config(page_title="AI Data Platform Catalog", page_icon="🧊", layout="wide")

AWS_REGION = os.getenv("AWS_REGION", "ap-south-1")
DATABASE_NAME = os.getenv("DATABASE_NAME", "dataplatform_dev_ai_catalog")
ATHENA_WORKGROUP = os.getenv("ATHENA_WORKGROUP", "primary")

# --- AWS Clients ---
@st.cache_resource
def get_glue_client()-> Any:
    """Caches the boto3 client to prevent re-initialization on every UI render."""
    return boto3.client("glue", region_name=AWS_REGION)

# --- Data Fetching Methods ---
@st.cache_data(ttl=300) # Cache for 5 minutes to reduce AWS API calls
def get_catalog_tables()-> list[str]:
    """Fetches all tables inside our Silver AI Catalog."""
    glue = get_glue_client()
    try:
        response: dict[str, Any] = glue.get_tables(DatabaseName=DATABASE_NAME)
        tables: list[str] = [table['Name'] for table in response.get('TableList', [])]
        return tables
    except ClientError as e:
        st.error(f"Failed to access Glue Catalog: {e}")
        return []

@st.cache_data(ttl=300)
def get_table_metadata(table_name: str)-> dict[str, Any]:
    """Retrieves AI-generated metadata and compliance status from the Glue Table properties."""
    glue = get_glue_client()
    try:
        response: dict[str, Any] = glue.get_table(DatabaseName=DATABASE_NAME, Name=table_name)
        params: dict[str, Any] = response['Table'].get('Parameters', {})
        return params
    except ClientError as e:
        st.error(f"Failed to fetch metadata for {table_name}: {e}")
        return {}

@st.cache_data(ttl=60)
def execute_athena_query(query: str)-> pd.DataFrame | None:
    """Executes an Athena query using AWS Wrangler and returns a Pandas DataFrame."""
    try:
        df: pd.DataFrame = wr.athena.read_sql_query(
            sql=query,
            database=DATABASE_NAME,
            workgroup=ATHENA_WORKGROUP,
            ctas_approach=False # Uses standard SELECT queries instead of CREATE TABLE AS
        )
        return df
    except Exception as e:
        st.error(f"Athena Query Failed: {str(e)}")
        return None

# --- UI Layout ---
st.title("🧊 Enterprise Data Discovery Catalog")
st.markdown("Explore Silver-tier Iceberg tables, view AI governance assessments, "
            "and query data directly.")

# Sidebar Navigation
st.sidebar.header("Data Catalog Navigation")
tables = get_catalog_tables()

if not tables:
    st.sidebar.warning(f"No tables found in database `{DATABASE_NAME}`.")
else:
    selected_table = st.sidebar.selectbox("Select a Table to Explore:", tables)

    if selected_table:
        st.header(f"Table: `{selected_table}`")

        # 1. Display Governance Metadata
        st.subheader("🤖 AI Governance Status")
        metadata = get_table_metadata(selected_table)

        # Look for the metadata injected by your Phase 3 Agent
        compliance = metadata.get("compliance_status", "UNKNOWN")
        null_ratio = metadata.get("calculated_null_ratio", "N/A")
        total_records = metadata.get("total_record_count", "N/A")

        col1, col2, col3 = st.columns(3)
        with col1:
            if compliance == "COMPLIANT":
                st.success("✅ COMPLIANT")
            elif compliance == "NON_COMPLIANT":
                st.error("❌ NON-COMPLIANT")
            else:
                st.warning("⚠️ UNKNOWN")
        with col2:
            st.metric(label="Total Records", value=total_records)
        with col3:
            st.metric(label="Null Ratio", value=null_ratio)

        # 2. Data Preview
        st.subheader("📊 Data Preview (Top 100 Rows)")
        with st.spinner("Querying Athena..."):
            preview_query = f'SELECT * FROM "{selected_table}" LIMIT 100'
            df_preview = execute_athena_query(preview_query)
            if df_preview is not None:
                st.dataframe(df_preview, use_container_width=True)

        # 3. Custom Query Interface
        st.subheader("🔍 Ad-Hoc Analysis")
        with st.expander("Write Custom SQL"):
            custom_query = st.text_area("SQL Query",
            value=f'SELECT COUNT(1) as total FROM "{selected_table}"', height=100)
            if st.button("Run Query", type="primary"):
                with st.spinner("Executing..."):
                    df_custom = execute_athena_query(custom_query)
                    if df_custom is not None:
                        st.dataframe(df_custom, use_container_width=True)
