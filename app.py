import streamlit as st
from mehricode import run

st.set_page_config(page_title="مِهرِي‑كود", layout="wide")

st.markdown("""
<style>
    html, body, [class*="css"] {
        direction: rtl;
        text-align: right;
    }
    textarea, input {
        direction: rtl !important;
        text-align: right !important;
        font-family: 'Amiri', 'Segoe UI', 'Tahoma', sans-serif !important;
        font-size: 17px !important;
        line-height: 1.9 !important;
    }
    pre, code, .stText {
        direction: rtl !important;
        text-align: right !important;
        font-family: 'Amiri', 'Segoe UI', 'Tahoma', sans-serif !important;
        font-size: 16px !important;
    }
    h1, h2, h3, h4, h5, h6, p, label {
        direction: rtl;
        text-align: right;
    }
    .stButton button {
        font-family: 'Amiri', 'Segoe UI', 'Tahoma', sans-serif;
        font-size: 16px;
    }
    .stAlert {
        direction: rtl;
        text-align: right;
    }
</style>
""", unsafe_allow_html=True)

st.title("مِهرِي‑كود — لغة برمجة باللسان المهري")

default_code = '''خلي اسم = ادخل();
اطبع("مرحبا " + اسم);

خلي أ = رقم(ادخل());
خلي ب = رقم(ادخل());
اطبع("المجموع = " + نص(أ + ب));
'''

code = st.text_area("الكود", height=320, value=default_code)
inputs = st.text_area("المدخلات (سطر لكل قيمة)", height=100, value="علي\n5\n7")

if st.button("شغّل"):
    outputs = []
    try:
        run(code, inputs.splitlines(), outputs.append)
        st.success("انتهى التنفيذ بنجاح")
        st.text("\n".join(outputs))
    except Exception as e:
        st.error(str(e))