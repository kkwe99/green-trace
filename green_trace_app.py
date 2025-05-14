import streamlit as st
import datetime
import streamlit_option_menu as option_menu
import geocoder
from PIL import Image
import io
import base64
import requests
import json

# 定義主色系
PRIMARY_COLOR = "#D32F2F"
SECONDARY_COLOR = "#FFFFFF"
ACCENT_COLOR = "#0D47A1"

st.set_page_config(page_title="GreenTrace", page_icon="🚑", layout="wide")

# CSS 設定
st.markdown(f"""
    <style>
        .main {{ background-color: {SECONDARY_COLOR}; }}
        h1, h2, h3, h4, h5, h6 {{ color: {PRIMARY_COLOR}; }}
        .stButton>button {{ background-color: {PRIMARY_COLOR}; color: {SECONDARY_COLOR}; }}
    </style>
""", unsafe_allow_html=True)

# 初始化 session_state
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "logout_confirm" not in st.session_state:
    st.session_state.logout_confirm = False
if "current_suggestion" not in st.session_state:
    st.session_state.current_suggestion = None
if "current_task" not in st.session_state:
    st.session_state.current_task = None
if "completed_tasks" not in st.session_state:
    st.session_state.completed_tasks = 0
if "users" not in st.session_state:
    st.session_state.users = []  # 儲存使用者資料
if "profile" not in st.session_state:
    st.session_state.profile = {"skill": "", "completed_tasks": 0, "volunteer_level": "初級志工"}

# 側邊導航
if not st.session_state.authenticated:
    menu_options = ["Login/Signup"]
    icons = ["box-arrow-in-right"]
else:
    menu_options = ["Emergency", "Tasks", "Legal Record", "Profile", "Logout"]
    icons = ["exclamation-triangle-fill", "list-task", "file-earmark-lock2", "person-circle", "box-arrow-left"]

with st.sidebar:
    selected = option_menu.option_menu(
        menu_title="GreenTrace",
        options=menu_options,
        icons=icons,
        menu_icon="heartbeat",
        default_index=0,
        styles={
            "container": {"background-color": "#f8f9fa"},
            "icon": {"color": PRIMARY_COLOR, "font-size": "24px"},
            "nav-link-selected": {"background-color": PRIMARY_COLOR}
        }
    )

# 顯示圖片
def display_image(image):
    img = Image.open(image)
    st.image(img, caption="已上傳的傷患照片", use_column_width=True)

# 將圖片轉為 base64
def image_to_base64(image):
    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()

# 透過 xAI API 獲取 LLM 建議
def get_llm_suggestion(description, image_base64=None):
    api_key = st.secrets.get("XAI_API_KEY", None)
    if not api_key:
        return "錯誤：未設定 xAI API 金鑰。請在 Streamlit 設定中新增 API 金鑰。"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    prompt = f"您是一位醫療急救專家。根據以下傷患描述：\n{description}\n請分析並提供具體的醫療建議。如果有圖片，請結合圖片內容進行分析。"
    
    payload = {
        "model": "grok-3",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt}
                ]
            }
        ]
    }
    
    if image_base64:
        payload["messages"][0]["content"].append({
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{image_base64}"}
        })
    
    try:
        response = requests.post("https://api.x.ai/v1/chat/completions", headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()
        return result["choices"][0]["message"]["content"]
    except Exception as e:
        return f"錯誤：無法獲取 LLM 建議。詳細錯誤：{str(e)}"

# 登入與註冊邏輯
if selected == "Login/Signup":
    st.title("GreenTrace - 登入/註冊")
    action = st.radio("想要登入還是註冊？", ("Login", "Signup"))

    if action == "Login":
        email = st.text_input("電子郵件")
        password = st.text_input("密碼", type="password")
        if st.button("登入"):
            user = next((u for u in st.session_state.users if u["email"] == email and u["password"] == password), None)
            if user:
                st.session_state.authenticated = True
                st.session_state.username = user["name"]
                st.session_state.profile = {
                    "skill": user.get("skill", ""),
                    "completed_tasks": int(user.get("completed_tasks", 0)),
                    "volunteer_level": user.get("volunteer_level", "初級志工")
                }
                st.success(f"歡迎回來，{user['name']}！請從左側選單繼續使用功能。")
                st.rerun()
            else:
                st.error("帳號或密碼錯誤")

    else:
        name = st.text_input("姓名")
        email = st.text_input("電子郵件")
        password = st.text_input("註冊密碼", type="password")
        confirm = st.text_input("確認密碼", type="password")
        if st.button("註冊"):
            if not name or not email or not password:
                st.warning("請完整填寫所有欄位")
            elif password != confirm:
                st.warning("兩次密碼不一致")
            elif any(u["email"] == email for u in st.session_state.users):
                st.warning("此 Email 已經註冊過")
            else:
                st.session_state.users.append({
                    "name": name,
                    "email": email,
                    "password": password,
                    "skill": "",
                    "completed_tasks": "0",
                    "volunteer_level": "初級志工"
                })
                st.success("✅ 註冊成功！請返回登入")

elif selected == "Logout":
    if not st.session_state.logout_confirm:
        st.warning("⚠️ 您即將登出系統。")
        if st.button("確定要登出嗎？"):
            st.session_state.logout_confirm = True
    else:
        st.markdown("### 您確定要登出嗎？")
        if st.button("是，我要登出"):
            st.session_state.authenticated = False
            st.session_state.username = ""
            st.session_state.logout_confirm = False
            st.session_state.profile = {"skill": "", "completed_tasks": 0, "volunteer_level": "初級志工"}
            st.success("您已成功登出。")
            st.rerun()
        
        with st.container():
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("否，回上一頁"):
                st.session_state.logout_confirm = False
                st.rerun()

# 處理 "Emergency"、"Tasks"、"Legal Record"、"Profile" 的邏輯
if st.session_state.authenticated:
    if selected == "Emergency":
        st.title("🚨 緊急通報")
        st.metric(label="當前位置", value="25.0478°N, 121.5319°E")
        g = geocoder.ip('me')
        if g.ok:
            lat, lon = g.latlng
            st.map({'lat': [lat], 'lon': [lon]})
        else:
            st.error("無法獲取當前位置，請檢查網絡或重新載入頁面")
        if st.button("一鍵求救"):
            st.success("緊急消息已發送！")

    elif selected == "Tasks":
        if st.session_state.current_task is None:
            st.title("🗒️ 任務清單")
            st.subheader("請選擇一項任務查看詳情")

            if st.button("🧭 安全屋路線協助"):
                st.session_state.current_task = "rescue_route"
                st.rerun()
            if st.button("🚦 協助交通指揮"):
                st.session_state.current_task = "traffic_control"
                st.rerun()
            if st.button("🩺 傷患狀況報告"):
                st.session_state.current_task = "medical_report"
                st.rerun()

        else:
            task = st.session_state.current_task
            if task == "rescue_route":
                st.title("🧭 安全屋路線協助")
                st.write("描述：協助指引受災民眾前往安全小屋...")
            elif task == "traffic_control":
                st.title("🚦 協助交通指揮")
                st.write("描述：支援現場交管與人員疏導...")
            elif task == "medical_report":
                st.title("🩺 傷患狀況報告")
                st.write("描述：協助紀錄並回報第一時間醫療狀況...")

                # 上傳傷患照片
                st.subheader("上傳傷患照片")
                uploaded_image = st.file_uploader("請上傳傷患照片", type=["jpg", "jpeg", "png"])
                if uploaded_image is not None:
                    display_image(uploaded_image)
                    image = Image.open(uploaded_image)
                    image_base64 = image_to_base64(image)
                    st.session_state.uploaded_image = image_base64
                    st.success("照片已上傳！")

                # AI 傷患處理建議
                st.subheader("AI 傷患處理建議")
                user_input = st.text_area("描述傷患具體狀況（例如：傷口位置、嚴重程度等）", "")
                if st.button("獲取 AI 建議"):
                    if not user_input and not hasattr(st.session_state, "uploaded_image"):
                        st.warning("請提供傷患描述或上傳照片以獲取建議。")
                    else:
                        image_base64 = st.session_state.uploaded_image if hasattr(st.session_state, "uploaded_image") else None
                        st.session_state.current_suggestion = get_llm_suggestion(user_input, image_base64)

                # 顯示當前建議
                if st.session_state.current_suggestion:
                    st.markdown(f"**AI 建議**：{st.session_state.current_suggestion}")

            st.markdown("---")
            if st.button("⬅ 返回任務列表"):
                st.session_state.current_task = None
                st.session_state.current_suggestion = None
                st.rerun()

            # 計算完成任務次數
            task_count = 0
            if task == "rescue_route":
                task_count += 1
            elif task == "traffic_control":
                task_count += 1
            elif task == "medical_report":
                task_count += 1

            if st.button("確認完成任務"):
                st.session_state.completed_tasks += task_count
                completed_tasks = st.session_state.completed_tasks
                if completed_tasks >= 20:
                    st.session_state.profile["volunteer_level"] = "金級志工"
                elif completed_tasks >= 10:
                    st.session_state.profile["volunteer_level"] = "銀級志工"
                else:
                    st.session_state.profile["volunteer_level"] = "初級志工"
                st.session_state.profile["completed_tasks"] = completed_tasks
                for user in st.session_state.users:
                    if user["name"] == st.session_state.username:
                        user["completed_tasks"] = str(completed_tasks)
                        user["volunteer_level"] = st.session_state.profile["volunteer_level"]
                st.success(f"已完成 {task_count} 個任務！您的志工等級：{st.session_state.profile['volunteer_level']}")

    elif selected == "Legal Record":
        st.title("📃 法律保障註記")
        st.text_area("現場行動自訴", "自願參與救援，保護傷者生命...")
        uploaded_files = st.file_uploader("上傳現場照片或錄音", accept_multiple_files=True)
        if st.button("確認儲存"):
            st.success("已儲存此次行動紀錄與資料！")

    elif selected == "Profile":
        st.title("👤 志工個人資料")
        st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/8/89/Portrait_Placeholder.png/480px-Portrait_Placeholder.png", width=150)
        st.header(st.session_state.username)

        st.write(f"志工等級：{st.session_state.profile['volunteer_level']}")
        st.write(f"參與任務：{st.session_state.profile['completed_tasks']} 次")
        st.write(f"專長技能：{st.session_state.profile['skill']}")

        st.subheader("更新個人資料")
        name = st.text_input("姓名", value=st.session_state.username)
        skill = st.text_input("專長技能", value=st.session_state.profile["skill"])
        if st.button("儲存更新"):
            st.session_state.profile["skill"] = skill
            st.session_state.username = name
            for user in st.session_state.users:
                if user["name"] == st.session_state.username:
                    user["name"] = name
                    user["skill"] = skill
            st.success("資料已更新")