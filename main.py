import telegram
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode
from telegram.error import BadRequest
import json
import random
import os
import asyncio
from gtts import gTTS
from dotenv import load_dotenv

# Завантажуємо змінні з .env файлу (наш "сейф")
load_dotenv()

# --- 1. Наші дані ---

VERBS = [
    ["see", "saw", "seen", "бачити"], ["cut", "cut", "cut", "різати"],
    ["go", "went", "gone", "йти"], ["do", "did", "done", "робити"],
    ["make", "made", "made", "створювати"], ["take", "took", "taken", "брати"],
    ["get", "got", "gotten", "отримувати"], ["give", "gave", "given", "давати"],
    ["come", "came", "come", "приходити"], ["think", "thought", "thought", "думати"],
    ["buy", "bought", "bought", "купувати"], ["eat", "ate", "eaten", "їсти"],
    ["drink", "drank", "drunk", "пити"], ["write", "wrote", "written", "писати"],
    ["read", "read", "read", "читати"], ["speak", "spoke", "spoken", "говорити"],
    ["know", "knew", "known", "знати"], ["find", "found", "found", "знаходити"],
    ["run", "ran", "run", "бігти"], ["begin", "began", "begun", "починати"]
]
PROGRESS_FILE = "user_progress.json"

# --- 2. Функції для роботи з прогресом ---

def load_progress():
    if not os.path.exists(PROGRESS_FILE): return {}
    try:
        with open(PROGRESS_FILE, 'r', encoding='utf-8') as f: return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError): return {}

def save_progress(data):
    with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# --- 3. Функції-обробники для бота ---

def create_audio_sync(text_to_speak, filename):
    """Синхронна функція для створення аудіо, щоб не блокувати основного бота."""
    tts = gTTS(text=text_to_speak, lang='en', slow=False)
    tts.save(filename)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробник команди /start. Встановлює постійну клавіатуру."""
    # ОНОВЛЕНА КЛАВІАТУРА: додано кнопку "Повторення слів"
    reply_keyboard = [
        [KeyboardButton("Вчити слова 🇬🇧"), KeyboardButton("Повторення слів 🔁")]
    ]
    welcome_text = (
        "Привіт! 🌟\n"
        "Я твій помічник у світі англійських неправильних дієслів!\n"
        "Разом ми вивчимо їх легко й весело 💫\n\n"
        "Натисни кнопку внизу — і вперед до нових знань! 🚀"
    )
    await update.message.reply_text(
        welcome_text,
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, resize_keyboard=True, one_time_keyboard=False
        ),
    )

async def send_new_verb_card(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Надсилає користувачу нову картку з дієсловом для вивчення."""
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    progress_data = load_progress()
    loop = asyncio.get_running_loop()

    known_verbs_infinitive = progress_data.get(user_id, [])
    unknown_verbs = [v for v in VERBS if v[0] not in known_verbs_infinitive]

    if not unknown_verbs:
        final_text = (
            "🎉 Ура! Ти вивчив(ла) всі 20 неправильних дієслів! �\n\n"
            "Це великий крок на шляху до вільної англійської 💫\n\n"
            "Вперед до нових вершин! 🏆"
        )
        await context.bot.send_message(chat_id=chat_id, text=final_text)
        return

    verb = random.choice(unknown_verbs)
    v1, v2, v3, translation = verb
    text_to_speak = f"{v1}, {v2}, {v3}"
    audio_filename = f"verb_audio_{user_id}.mp3"
    
    await loop.run_in_executor(None, create_audio_sync, text_to_speak, audio_filename)
    
    verb_caption = (
        f"📝 *{v1.upper()} - {v2.upper()} - {v3.upper()}*\n\n"
        f"Переклад: *{translation}*"
    )
    keyboard = [
        [InlineKeyboardButton("✅ Знаю це дієслово", callback_data=f'know_{v1}')],
        [InlineKeyboardButton("➡️ Наступне дієслово", callback_data='learn_word')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    with open(audio_filename, 'rb') as audio_file:
        await context.bot.send_audio(
            chat_id=chat_id, audio=audio_file,
            caption=verb_caption, reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    os.remove(audio_filename)

async def send_repetition_verb_card(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Надсилає картку з дієсловом для повторення."""
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    progress_data = load_progress()
    loop = asyncio.get_running_loop()

    known_verbs_infinitive = progress_data.get(user_id, [])
    
    if not known_verbs_infinitive:
        await context.bot.send_message(
            chat_id=chat_id,
            text="Ви ще не вивчили жодного слова. Натисніть 'Вчити слова 🇬🇧', щоб почати!"
        )
        return

    # Вибираємо випадкове слово зі списку вивчених
    random_verb_infinitive = random.choice(known_verbs_infinitive)
    verb = next((v for v in VERBS if v[0] == random_verb_infinitive), None)

    if not verb: return # Про всяк випадок, якщо слово не знайдено

    v1, v2, v3, translation = verb
    text_to_speak = f"{v1}, {v2}, {v3}"
    audio_filename = f"verb_audio_{user_id}.mp3"
    
    await loop.run_in_executor(None, create_audio_sync, text_to_speak, audio_filename)
    
    verb_caption = (
        f"📝 *{v1.upper()} - {v2.upper()} - {v3.upper()}*\n\n"
        f"Переклад: *{translation}*"
    )
    # Клавіатура для режиму повторення
    keyboard = [
        [InlineKeyboardButton("➡️ Наступне для повторення", callback_data='repeat_word')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    with open(audio_filename, 'rb') as audio_file:
        await context.bot.send_audio(
            chat_id=chat_id, audio=audio_file,
            caption=verb_caption, reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    os.remove(audio_filename)

async def inline_button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробляє натискання на inline-кнопки."""
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    
    try:
        await query.message.delete()
    except BadRequest:
        pass

    # Логіка для вивчення нових слів
    if query.data.startswith('know_') or query.data == 'learn_word':
        if query.data.startswith('know_'):
            verb_to_add = query.data.split('_')[1]
            progress_data = load_progress()
            if user_id not in progress_data:
                progress_data[user_id] = []
            if verb_to_add not in progress_data[user_id]:
                progress_data[user_id].append(verb_to_add)
            save_progress(progress_data)
        await send_new_verb_card(update, context)

    # Логіка для повторення слів
    elif query.data == 'repeat_word':
        await send_repetition_verb_card(update, context)

# --- 4. Основна частина для запуску бота ---

def main():
    """Запускає бота."""
    TOKEN = os.getenv("TELEGRAM_TOKEN")
    if not TOKEN:
        print("Помилка: Не знайдено TELEGRAM_TOKEN. Перевірте ваш .env файл.")
        return

    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    # Обробники для постійних кнопок
    application.add_handler(MessageHandler(filters.Regex("^Вчити слова 🇬🇧$"), send_new_verb_card))
    application.add_handler(MessageHandler(filters.Regex("^Повторення слів 🔁$"), send_repetition_verb_card))
    # Обробник для всіх inline-кнопок
    application.add_handler(CallbackQueryHandler(inline_button_callback))
    
    print("Бот запущений і готовий до роботи...")
    application.run_polling()

if __name__ == '__main__':
    main()
    