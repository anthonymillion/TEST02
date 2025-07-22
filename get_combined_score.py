# === Dark Theme Table Styling ===
st.markdown("""
    <style>
    .dataframe th, .dataframe td {
        text-align: center !important;
        color: #ddd !important;
        background-color: #111 !important;
        border-color: #333 !important;
        font-size: 14px;
    }
    .dataframe th {
        background-color: #222 !important;
        font-weight: bold;
    }
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 0rem !important;
    }
    h3 {
        margin-bottom: 0.2rem !important;
    }
    .stDataFrame {
        margin-bottom: 0rem !important;
    }
    </style>
""", unsafe_allow_html=True)

# === Display Stocks Table ===
st.markdown("### 📈 NASDAQ-100 Stocks")
st.dataframe(
    pd.DataFrame([process_symbol(sym) for sym in stock_list])
    .sort_values("Score", ascending=False)
    .reset_index(drop=True),
    use_container_width=True,
    hide_index=True
)

# === Display Global Market Symbols Table ===
st.markdown("### 🌐 Global Market Symbols")
st.dataframe(
    pd.DataFrame([process_symbol(tick, name, is_macro=True) for name, tick in macro_symbols.items()])
    .sort_values("Score", ascending=False)
    .reset_index(drop=True),
    use_container_width=True,
    hide_index=True
)
