import streamlit as st
from agents.supervisor_agent import handle_query

st.title("AI Audit Assistant")

# =========================
# SESSION STATE
# =========================

if "past_inputs" not in st.session_state:
    st.session_state.past_inputs = []

# =========================
# DASHBOARD
# =========================

st.subheader("Audit Dashboard")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Total Queries", len(st.session_state.past_inputs))

with col2:
    st.metric("Workpapers Reviewed", len(st.session_state.past_inputs) * 3)

with col3:
    st.metric("High Risk Controls", len(st.session_state.past_inputs))

# =========================
# INPUT BOX
# =========================

query = st.text_input("Enter audit query")

# =========================
# RUN BUTTON
# =========================

if st.button("Run"):

    if query.strip() != "":

        # Save input history
        st.session_state.past_inputs.append(query)

        # Run agents
        result, suggestions = handle_query(query)

        # Show suggestions
        if len(suggestions) > 0:

            st.subheader("Search Suggestions")

            for suggestion in suggestions:
                st.write("- " + suggestion)

        # Show response
        st.subheader("Response")
        st.write(result)

# =========================
# PREVIOUS INPUTS
# =========================

st.subheader("Previous ")

for item in reversed(st.session_state.past_inputs):
    st.write("- " + item)