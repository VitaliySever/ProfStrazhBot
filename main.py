
import telebot
import re
from telebot import types
from fz77_articles import fz77_articles
from instructions import instructions
from safety_measures import safety_text
from training_data_full import training_questions
from openai import OpenAI

BOT_TOKEN = "7774427933:AAHlvFH6atbprmpLY7EK2vw5Rsth1hJl974"
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown")

client = OpenAI(
    api_key="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",
    base_url="https://openrouter.ai/api/v1"
)

user_context = {}

def main_keyboard():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("🗣 Задай вопрос", "📘 ФЗ-77")
    kb.row("✍️ Объяснительная", "🛡 Меры безопасности")
    kb.row("📚 Обучение")
    return kb

def back_keyboard():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("🔙 Назад в меню")
    return kb

@bot.message_handler(commands=["start"])
def send_welcome(message):
    bot.send_message(
        message.chat.id,
       "Здравствуйте! Я — ПрофСтраж."

"
        "Я помогу вам:
"
        "— Ответить на вопросы по `ФЗ-77`
"
        "— Получить консультацию по охране труда, оружию, ЧС
"
        "— Написать объяснительную или задать вопрос

"
        "Выберите действие кнопками ниже.",
        reply_markup=main_keyboard()
    )

@bot.message_handler(commands=["фз77"])
def fz77_short(message):
    parts = message.text.split()
    if len(parts) == 2 and parts[1].isdigit():
        article = fz77_articles.get(parts[1])
        if article:
            bot.send_message(message.chat.id, article)
        else:
            bot.send_message(message.chat.id, "Извините, такой статьи нет.")
    else:
        bot.send_message(message.chat.id, "Напишите команду так: /фз77 12")

@bot.message_handler(func=lambda m: m.text in [
    "🗣 Задай вопрос", "📘 ФЗ-77", "✍️ Объяснительная", "🛡 Меры безопасности", "📚 Обучение", "🔙 Назад в меню"
])
def menu_buttons(message):
    user_id = message.chat.id
    if message.text == "📘 ФЗ-77":
        user_context[user_id] = "fz77"
        bot.send_message(user_id, "Укажите номер статьи, например: 'Статья 5', 'ст. 5 ФЗ-77' или просто '5 фз'.")
    elif message.text == "🗣 Задай вопрос":
        user_context[user_id] = "question"
        bot.send_message(user_id, "Задайте свой вопрос — я постараюсь ответить грамотно и по делу.")
    elif message.text == "✍️ Объяснительная":
        user_context[user_id] = "explanatory"
        bot.send_message(user_id, "Опишите ситуацию, по которой требуется объяснительная — я помогу составить официальный текст.")
    elif message.text == "🛡 Меры безопасности":
        chunks = [safety_text[i:i + 4000] for i in range(0, len(safety_text), 4000)]
        for part in chunks:
            bot.send_message(user_id, part)
        bot.send_message(user_id, "Чтобы вернуться в меню, нажмите кнопку ниже ⬇️", reply_markup=back_keyboard())
    elif message.text == "📚 Обучение":
        user_context[user_id] = "training"
        bot.send_message(user_id, "Введите вопрос — я найду ответ в обучающем материале.")
    elif message.text == "🔙 Назад в меню":
        user_context[user_id] = None
        bot.send_message(user_id, "Выберите действие:", reply_markup=main_keyboard())

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = message.chat.id
    user_mode = user_context.get(user_id)

    if not user_mode:
        bot.send_message(user_id, "Пожалуйста, выберите действие кнопками ниже.", reply_markup=main_keyboard())
        return

    text = message.text.strip().lower()

    if user_mode == "fz77":
        match = re.search(r'(?:ст\.?\s*|статья\s*)?(\d{1,2})(?=\D*фз\s*-?\s*77|\s*фз\s*|\s*-?фз)?', text)
        if match:
            num = match.group(1)
            article = fz77_articles.get(num)
            if article:
                bot.send_message(user_id, article)
            else:
                bot.send_message(user_id, "Извините, такой статьи в ФЗ-77 нет.")
        else:
            bot.send_message(user_id, "Не удалось распознать номер статьи. Пример: 'статья 6 ФЗ-77'.")

    elif user_mode == "explanatory":
        found = None
        for key in instructions:
            if key.lower() in text:
                found = instructions[key]
                break
        if found:
            bot.send_message(user_id, found)
        else:
            try:
                response = client.chat.completions.create(
                    model="mistralai/mixtral-8x7b-instruct",
                    messages=[
                        {
                            "role": "system",
                            "content": "Ты помощник сотрудника ведомственной охраны. Отвечай строго на русском языке. Если просят составить объяснительную — делай это официально, без шаблонов. Всегда вставай на сторону охранника."
                        },
                        {"role": "user", "content": message.text}
                    ]
                )
                answer = response.choices[0].message.content
                bot.send_message(user_id, answer)
            except Exception as e:
                bot.send_message(user_id, f"⚠️ Ошибка при обращении к ИИ:\n{e}")

    elif user_mode == "question":
        found = None
        for key in instructions:
            if key.lower() in text:
                found = instructions[key]
                break
        if found:
            bot.send_message(user_id, found)
        else:
            try:
                response = client.chat.completions.create(
                    model="mistralai/mixtral-8x7b-instruct",
                    messages=[
                        {
                            "role": "system",
                            "content": "Ты помощник сотрудника ведомственной охраны. Консультируй грамотно и официально. Не пиши объяснительные."
                        },
                        {"role": "user", "content": message.text}
                    ]
                )
                answer = response.choices[0].message.content
                bot.send_message(user_id, answer)
            except Exception as e:
                bot.send_message(user_id, f"⚠️ Ошибка при обращении к ИИ:\n{e}")

    elif user_mode == "training":
        found = None
        for q in training_questions:
            if all(word in q for word in text.split()):
                found = training_questions[q]
                break
        if found:
            bot.send_message(user_id, found)
        else:
            bot.send_message(user_id, "❓ Вопрос не найден. Попробуйте задать иначе.")

if __name__ == "__main__":
    print("ПрофСтраж на связи! Всё работает.")
    while True:
        try:
            bot.polling(none_stop=True)
        except Exception as e:
            print(f"Ошибка: {e}")
