import os
import streamlit as st
import yadisk
import json
import io
import streamlit.components.v1 as components 
from openai import OpenAI
from dotenv import load_dotenv

# --- Адаптация для работы локально и в облаке ---
load_dotenv() 

def get_secret(key):
    # Пытаемся получить секрет из облака (st.secrets)
    try:
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        # Если файла секретов нет (локальный запуск), просто пропускаем ошибку
        pass
    
    # Если не нашли в облаке (или запущено локально), берем из .env
    return os.getenv(key)

# --- Настройки страницы ---
st.set_page_config(page_title="Анализ Индивидов", page_icon="🧠", layout="wide")

# --- ПРОВЕРКА АВТОРИЗАЦИИ ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🔒 Вход в систему")
    st.markdown("Для доступа к анализу индивидов, пожалуйста, введите код доступа.")
    
    password_input = st.text_input("Код доступа:", type="password")
    
    if st.button("Войти", type="primary"):
        if password_input == get_secret("APP_PASSWORD"):
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("❌ Неверный код доступа")
            
    st.stop()

# --- Инициализация клиентов ---
YANDEX_TOKEN = get_secret("YANDEX_DISK_TOKEN")
OPENROUTER_KEY = get_secret("OPENROUTER_API_KEY")

client = OpenAI(
    api_key=OPENROUTER_KEY,
    base_url="https://openrouter.ai/api/v1"
)

y = yadisk.YaDisk(token=YANDEX_TOKEN) if YANDEX_TOKEN else None

# --- Функции для работы с Яндекс.Диском ---
@st.cache_data(ttl=600)
def get_files_from_yadisk(folder_path):
    if not y:
        return []
    try:
        items = list(y.listdir(folder_path))
        files = [item.name for item in items if item.type == "file" and item.name.endswith('.txt')]
        return sorted(files)
    except Exception as e:
        st.error(f"Ошибка доступа к Яндекс.Диску: {e}")
        return []

@st.cache_data(ttl=600)
def read_file_from_yadisk(file_path):
    if not y:
        return "Ошибка: нет соединения с Яндекс.Диском."
    try:
        buffer = io.BytesIO()
        y.download(file_path, buffer)
        return buffer.getvalue().decode('utf-8')
    except Exception as e:
        return f"Ошибка чтения файла {file_path}: {e}"

# --- Пути к папкам ---
PATH_CAT1 = "/Categories_Mudra/Category_1" 
PATH_CAT2 = "/Categories_Mudra/Category_2" 
PATH_CAT3 = "/Categories_Mudra/Category_3" 
PATH_CAT4 = "/Categories_Mudra/Category_4" 

files_cat1 = get_files_from_yadisk(PATH_CAT1)
files_cat2 = get_files_from_yadisk(PATH_CAT2)
files_cat3 = get_files_from_yadisk(PATH_CAT3)
files_cat4 = get_files_from_yadisk(PATH_CAT4)

# --- БОКОВАЯ ПАНЕЛЬ ---
with st.sidebar:
    st.header("⚙️ Настройки")
    
    # Кнопка "Новый анализ" в самом верху
    if st.button("🔄 Новый анализ", type="primary", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

    if st.button("🚪 Выйти", use_container_width=True):
        st.session_state.authenticated = False
        st.session_state.messages = []
        st.rerun()
        
    st.divider()
    st.subheader("👤 Индивид 1")
    ind1_f1 = st.selectbox("Category 1 (Тип)", files_cat1, key="i1f1")
    ind1_f2 = st.selectbox("Category 2 (Ценность)", files_cat2, key="i1f2")
    ind1_f3 = st.selectbox("Category 3 (Сила)", files_cat3, key="i1f3")
    ind1_f4 = st.selectbox("Category 4 (КИ/ПИ/ЭИ)", files_cat4, key="i1f4")
    
    st.divider()
    st.subheader("👥 Индивид 2") # Убрали "(Опционально)"
    use_ind2 = st.checkbox("Добавить второго индивида")
    ind2_f1 = st.selectbox("Category 1 (Тип)", files_cat1, key="i2f1", disabled=not use_ind2)
    ind2_f2 = st.selectbox("Category 2 (Ценность)", files_cat2, key="i2f2", disabled=not use_ind2)
    ind2_f3 = st.selectbox("Category 3 (Сила)", files_cat3, key="i2f3", disabled=not use_ind2)
    ind2_f4 = st.selectbox("Category 4 (КИ/ПИ/ЭИ)", files_cat4, key="i2f4", disabled=not use_ind2)

# --- ОСНОВНОЙ ЭКРАН (Чат) ---
st.title("🧠 Анализ Индивидов")
st.markdown("Выберите файлы в левой панели и задайте вопрос в чате ниже.")

if "messages" not in st.session_state:
    st.session_state.messages = []

# Отображаем историю сообщений
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Поле ввода для чата
if prompt := st.chat_input("Задайте вопрос..."):
    # 1. Добавляем сообщение пользователя в историю
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2. Готовим контекст и получаем ответ
    with st.chat_message("assistant"):
        with st.spinner("Анализирую файлы..."):
            context = ""
            context += "--- ИНДИВИД 1 ---\n"
            for f in [ind1_f1, ind1_f2, ind1_f3, ind1_f4]:
                if f:
                    context += read_file_from_yadisk(f"{PATH_CAT1}/{f}") + "\n"
            
            if use_ind2:
                context += "\n--- ИНДИВИД 2 ---\n"
                for f in [ind2_f1, ind2_f2, ind2_f3, ind2_f4]:
                    if f:
                        context += read_file_from_yadisk(f"{PATH_CAT1}/{f}") + "\n"

            system_prompt = f"Ты — профессиональный аналитик. Вот информация о человеке (или двух):\n{context}\n\nОтвечай на вопросы пользователя, опираясь на эту информацию."
            
            api_messages = [{"role": "system", "content": system_prompt}] + st.session_state.messages

            try:
                response = client.chat.completions.create(
                    model="openrouter/free",
                    messages=api_messages,
                    temperature=0.7
                )
                
                answer_text = response.choices[0].message.content
                
                # Очистка текста от HTML-тегов
                answer_text = answer_text.replace("<br>", "\n").replace("<br/>", "\n").replace("<br />", "\n")
                answer_text = answer_text.replace("•", "-")
                
                # Отображаем ответ
                st.markdown(answer_text)
                
                # Добавляем ответ в историю
                st.session_state.messages.append({"role": "assistant", "content": answer_text})
                
                # --- Кнопка Копировать (сохраняет структуру) ---
                # json.dumps безопасно экранирует все переносы строк \n и кавычки для JS
                js_text = json.dumps(answer_text) 
                copy_html = f"""
                <button onclick="copyToClipboard(this)" style="width: auto; padding: 0 15px; height: 30px; background-color: transparent; color: #ff4b4b; border: 1px solid #ff4b4b; border-radius: 0.25rem; cursor: pointer; font-size: 14px; font-family: 'Source Sans Pro', sans-serif; margin-top: 5px;">
                    📋 Копировать текст
                </button>
                <script>
                function copyToClipboard(btn) {{
                    navigator.clipboard.writeText({js_text}).then(function() {{
                        const originalText = btn.innerHTML;
                        btn.innerHTML = '✅ Скопировано!';
                        btn.style.backgroundColor = '#28a745';
                        btn.style.color = 'white';
                        btn.style.borderColor = '#28a745';
                        setTimeout(() => {{
                            btn.innerHTML = originalText;
                            btn.style.backgroundColor = 'transparent';
                            btn.style.color = '#ff4b4b';
                            btn.style.borderColor = '#ff4b4b';
                        }}, 2000);
                    }}, function(err) {{
                        console.error('Ошибка: ', err);
                    }});
                }}
                </script>
                """
                components.html(copy_html, height=35)
                
            except Exception as e:
                st.error(f"Ошибка при обращении к нейросети: {e}")