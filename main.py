import telebot
import os
import re
from fz77_articles import fz77_articles
from instructions import instructions
from safety_measures import safety_text
from training_data_full import training_questions
from openai import OpenAI

BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENROUTER_API_KEY")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown")

client = OpenAI(
    api_key=OPENAI_API_KEY,
    base_url="https://openrouter.ai/api/v1"
)

user_context = {}

def main_keyboard():
    kb = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("🗣 Задай вопрос", "📘 ФЗ-77")
    kb.row("✍️ Объяснительная", "🛡 Меры безопасности")
    kb.row("📚 Обучение")
    return kb

def back_keyboard():
    kb = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("🔙 Назад в меню")
    return kb

@bot.message_handler(commands=["start"])
def send_welcome(message):
    bot.send_message(
        message.chat.id,
        "*Здравствуйте! Я — ПрофСтраж.*\n\n"
        "Я помогу вам:\n"
        "— Ответить на вопросы по `ФЗ-77`\n"
        "— Получить консультацию по охране труда, оружию, ЧС\n"
        "— Написать объяснительную или задать вопрос\n\n"
        "Выберите действие кнопками ниже.",
        reply_markup=main_keyboard()
    )

@bot.message_handler(func=lambda m: m.text in ["🗣 Задай вопрос", "📘 ФЗ-77", "✍️ Объяснительная", "🛡 Меры безопасности", "📚 Обучение", "🔙 Назад в меню"])
def menu_buttons(message):
    user_id = message.chat.id
    if message.text == "📘 ФЗ-77":
        user_context[user_id] = "fz77"
        bot.send_message(user_id, "Укажите номер статьи, например: 'статья 5 ФЗ-77'")
    elif message.text == "🗣 Задай вопрос":
        user_context[user_id] = "question"
        bot.send_message(user_id, "Задайте вопрос — я подключу ИИ и отвечу.")
    elif message.text == "✍️ Объяснительная":
        user_context[user_id] = "explanatory"
        bot.send_message(user_id, "Опишите ситуацию — составлю объяснительную.")
    elif message.text == "🛡 Меры безопасности":
        chunks = [safety_text[i:i+4000] for i in range(0, len(safety_text), 4000)]
        for part in chunks:
            bot.send_message(user_id, part)
        bot.send_message(user_id, "Чтобы вернуться в меню, нажмите кнопку ниже ⬇️", reply_markup=back_keyboard())
    elif message.text == "📚 Обучение":
        user_context[user_id] = "training"
        bot.send_message(user_id, "Введите учебный вопрос — я найду ответ.")
    elif message.text == "🔙 Назад в меню":
        user_context[user_id] = None
        bot.send_message(user_id, "Выберите действие:", reply_markup=main_keyboard())

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = message.chat.id
    user_mode = user_context.get(user_id)
    text = message.text.strip().lower()

    if not user_mode:
        bot.send_message(user_id, "Выберите действие:", reply_markup=main_keyboard())
        return

    if user_mode == "fz77":
        match = re.search(r"(?:статья\s*)?(\d+)", text)
        if match:
            num = match.group(1)
            article = fz77_articles.get(num)
            bot.send_message(user_id, article if article else "Такой статьи нет.")
        else:
            bot.send_message(user_id, "Пример: 'статья 6 ФЗ-77'")
    elif user_mode in ["question", "explanatory"]:
        try:
            response = client.chat.completions.create(
                model="mistralai/mixtral-8x7b-instruct",
                messages=[
                    {"role": "system", "content": "Ты помощник сотрудника охраны. Отвечай строго на русском, официально."},
                    {"role": "user", "content": message.text}
                ]
            )
            answer = response.choices[0].message.content
            bot.send_message(user_id, answer)
        except Exception as e:
            bot.send_message(user_id, f"⚠️ Ошибка ИИ: {e}")
    elif user_mode == "training":
        found = None
        for q in training_questions:
            if all(word in q for word in text.split()):
                found = training_questions[q]
                break
        bot.send_message(user_id, found or "Вопрос не найден. Попробуйте иначе.")

if __name__ == "__main__":
    print("ProfStrazhBot запущен!")
    bot.polling(none_stop=True)