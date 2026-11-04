import os
import streamlit as st
import yadisk
import json
import io
import streamlit.components.v1 as components 
from openai import OpenAI
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# --- Настройки страницы (должны быть в самом начале) ---
st.set_page_config(page_title="Анализ Индивидов", page_icon="🧠", layout="wide")

# --- ПРОВЕРКА АВТОРИЗАЦИИ ---
# Инициализируем состояние, если его еще нет
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

# Если пользователь не авторизован, показываем экран входа
if not st.session_state.authenticated:
    st.title("🔒 Вход в систему")
    st.markdown("Для доступа к анализу индивидов, пожалуйста, введите код доступа.")
    
    password_input = st.text_input("Код доступа:", type="password")
    
    if st.button("Войти", type="primary"):
        # Сравниваем введенный пароль с тем, что в .env
        if password_input == os.getenv("APP_PASSWORD"):
            st.session_state.authenticated = True
            st.rerun() # Перезагружаем страницу, чтобы убрать экран входа
        else:
            st.error("❌ Неверный код доступа")
            
    st.stop() # Останавливаем выполнение кода, пока не введен пароль

# --- Инициализация клиентов (выполняется только после входа) ---
YANDEX_TOKEN = os.getenv("YANDEX_DISK_TOKEN")
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY")

client = OpenAI(
    api_key=OPENROUTER_KEY,
    base_url="https://openrouter.ai/api/v1"
)

y = yadisk.YaDisk(token=YANDEX_TOKEN) if YANDEX_TOKEN else None

# --- Функции для работы с Яндекс.Диском ---
@st.cache_data(ttl=600)
def get_files_from_yadisk(folder_path):
    if not y:
        st.error("Токен Яндекс.Диска не найден.")
        return []
    try:
        items = list(y.listdir(folder_path))
        files = [item.name for item in items if item.type == "file" and item.name.endswith('.txt')]
        return sorted(files)
    except Exception as e:
        st.error(f"Ошибка доступа к Яндекс.Диску: {e}")
        return []

def read_file_from_yadisk(file_path):
    if not y:
        return "Ошибка: нет соединения с Яндекс.Диском."
    try:
        buffer = io.BytesIO()
        y.download(file_path, buffer)
        return buffer.getvalue().decode('utf-8')
    except Exception as e:
        return f"Ошибка чтения файла {file_path}: {e}"

# --- Основной интерфейс ---
# Добавляем кнопку "Выйти" в боковую панель
with st.sidebar:
    st.write(f"Вы вошли как: Гость")
    if st.button("🚪 Выйти"):
        st.session_state.authenticated = False
        st.rerun()

st.title("🧠 Анализ Индивидов по категориям")
st.markdown("Выберите файлы для одного или двух индивидов и задайте вопрос нейросети.")

# --- Пути к папкам ---
PATH_CAT1 = "/Categories_Mudra/Category_1" 
PATH_CAT2 = "/Categories_Mudra/Category_2" 
PATH_CAT3 = "/Categories_Mudra/Category_3" 
PATH_CAT4 = "/Categories_Mudra/Category_4" 

files_cat1 = get_files_from_yadisk(PATH_CAT1)
files_cat2 = get_files_from_yadisk(PATH_CAT2)
files_cat3 = get_files_from_yadisk(PATH_CAT3)
files_cat4 = get_files_from_yadisk(PATH_CAT4)

col1, col2 = st.columns(2)

with col1:
    st.header("👤 Индивид 1")
    ind1_f1 = st.selectbox("Category 1 (Тип)", files_cat1, key="i1f1")
    ind1_f2 = st.selectbox("Category 2 (Ценность)", files_cat2, key="i1f2")
    ind1_f3 = st.selectbox("Category 3 (Сила)", files_cat3, key="i1f3")
    ind1_f4 = st.selectbox("Category 4 (КИ/ПИ/ЭИ)", files_cat4, key="i1f4")

with col2:
    st.header("👥 Индивид 2 (Опционально)")
    use_ind2 = st.checkbox("Добавить второго индивида для анализа конфликтов")
    ind2_f1 = st.selectbox("Category 1 (Тип)", files_cat1, key="i2f1", disabled=not use_ind2)
    ind2_f2 = st.selectbox("Category 2 (Ценность)", files_cat2, key="i2f2", disabled=not use_ind2)
    ind2_f3 = st.selectbox("Category 3 (Сила)", files_cat3, key="i2f3", disabled=not use_ind2)
    ind2_f4 = st.selectbox("Category 4 (КИ/ПИ/ЭИ)", files_cat4, key="i2f4", disabled=not use_ind2)

st.divider()
question = st.text_area("Ваш вопрос:", placeholder="Например: Какие профессии подходят этому человеку? Или: Какие конфликты возможны между ними?")

if st.button("Запустить анализ", type="primary"):
    if not question:
        st.warning("Пожалуйста, напишите вопрос.")
    else:
        with st.spinner("Читаю файлы с Яндекс.Диска и анализирую..."):
            context = ""
            
            context += "--- ИНДИВИД 1 ---\n"
            for f in [ind1_f1, ind1_f2, ind1_f3, ind1_f4]:
                if f:
                    full_path = f"{PATH_CAT1}/{f}" if PATH_CAT1 else f"/{f}"
                    context += read_file_from_yadisk(full_path) + "\n"
            
            if use_ind2:
                context += "\n--- ИНДИВИД 2 ---\n"
                for f in [ind2_f1, ind2_f2, ind2_f3, ind2_f4]:
                    if f:
                        full_path = f"{PATH_CAT1}/{f}" if PATH_CAT1 else f"/{f}"
                        context += read_file_from_yadisk(full_path) + "\n"

            system_prompt = "Ты — профессиональный аналитик. На основе предоставленной информации о человеке (или двух людях) дай развернутый и структурированный ответ на вопрос пользователя."
            
            try:
                response = client.chat.completions.create(
                    model="openrouter/free",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"Вот информация:\n{context}\n\nВопрос: {question}"}
                    ],
                    temperature=0.7
                )
                
                answer_text = response.choices[0].message.content
                
                # Очистка текста
                answer_text = answer_text.replace("<br>", "\n").replace("<br/>", "\n").replace("<br />", "\n")
                answer_text = answer_text.replace("•", "-")
                
                st.success("Анализ завершен!")
                st.markdown("### Ответ нейросети:")
                st.markdown(answer_text)
                
                st.divider()
                
                btn_col1, btn_col2 = st.columns(2)
                
                with btn_col1:
                    st.download_button(
                        label="📥 Скачать ответ в файл (.txt)",
                        data=answer_text,
                        file_name="Анализ_Индивидов.txt",
                        mime="text/plain",
                        type="primary",
                        use_container_width=True
                    )
                
                with btn_col2:
                    js_text = json.dumps(answer_text) 
                    copy_html = f"""
                    <button onclick="copyToClipboard(this)" style="width: 100%; height: 38px; background-color: #ff4b4b; color: white; border: none; border-radius: 0.25rem; cursor: pointer; font-weight: 400; font-family: 'Source Sans Pro', sans-serif;">
                        📋 Копировать текст
                    </button>
                    <script>
                    function copyToClipboard(btn) {{
                        navigator.clipboard.writeText({js_text}).then(function() {{
                            const originalText = btn.innerHTML;
                            btn.innerHTML = '✅ Скопировано!';
                            btn.style.backgroundColor = '#28a745';
                            setTimeout(() => {{
                                btn.innerHTML = originalText;
                                btn.style.backgroundColor = '#ff4b4b';
                            }}, 2000);
                        }}, function(err) {{
                            console.error('Ошибка копирования: ', err);
                        }});
                    }}
                    </script>
                    """
                    components.html(copy_html, height=45)
                
            except Exception as e:
                st.error(f"Ошибка при обращении к нейросети: {e}")