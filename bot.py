import logging
import os
from groq import Groq
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# ============================
# ВСТАВЬ СВОИ КЛЮЧИ СЮДА
# ============================
TELEGRAM_TOKEN = "8647995056:AAFNCf4_4oV5KIY0XimS_RH82hrs8cwBsF8"
GROQ_API_KEY = "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"

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

def main_keyboard():
    keyboard = [
        [KeyboardButton("🍽 Что приготовить?")],
        [KeyboardButton("⚡ Быстрый рецепт"), KeyboardButton("🥗 Вегетарианское")],
        [KeyboardButton("🍳 На завтрак"), KeyboardButton("🍲 На ужин")],
        [KeyboardButton("ℹ️ Помощь")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_recipe(products: str, filter_type: str = "") -> str:
    client = Groq(api_key=GROQ_API_KEY)
    filter_text = ""
    if filter_type == "fast":
        filter_text = "Рецепт должен готовиться не более 20 минут."
    elif filter_type == "veg":
        filter_text = "Рецепт должен быть вегетарианским."
    elif filter_type == "breakfast":
        filter_text = "Рецепт должен подходить для завтрака."
    elif filter_type == "dinner":
        filter_text = "Рецепт должен подходить для ужина."

    prompt = f"""У меня есть такие продукты: {products}
{filter_text}
Придумай один вкусный рецепт. Формат ответа:

🍽 Название блюда
⏱ Время: ...
👥 Порции: ...
🔥 Калории: ...

📝 Ингредиенты:
- ...

👨‍🍳 Приготовление:
1. ...

💡 Совет: ...

Отвечай на русском языке."""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1000
    )
    return response.choices[0].message.content

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.effective_user.first_name
    await update.message.reply_text(
        f"👋 Привет, {user_name}!\n\nЯ бот-помощник по готовке 🍳\n\nНапиши продукты которые есть дома и я предложу рецепт!\n\nНапример: картошка, яйца, лук",
        reply_markup=main_keyboard()
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "ℹ️ Напиши продукты через запятую и получи рецепт!\n\nПример: курица, рис, морковь\n\n⚡ Быстрый — за 20 минут\n🥗 Вегетарианское — без мяса\n🍳 Завтрак / 🍲 Ужин"
    )

async def handle_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text

    menu_buttons = {
        "🍽 Что приготовить?": ("", "🍽 Напиши продукты которые есть дома:"),
        "⚡ Быстрый рецепт": ("fast", "⚡ Напиши продукты (рецепт за 20 минут):"),
        "🥗 Вегетарианское": ("veg", "🥗 Напиши продукты (вегетарианский рецепт):"),
        "🍳 На завтрак": ("breakfast", "🍳 Напиши продукты (рецепт для завтрака):"),
        "🍲 На ужин": ("dinner", "🍲 Напиши продукты (рецепт для ужина):"),
    }

    if user_text in menu_buttons:
        filter_type, reply_text = menu_buttons[user_text]
        context.user_data["filter"] = filter_type
        await update.message.reply_text(reply_text)
        return

    if user_text == "ℹ️ Помощь":
        await help_command(update, context)
        return

    if len(user_text) < 3:
        await update.message.reply_text("Напиши продукты через запятую 🥕")
        return

    thinking_msg = await update.message.reply_text("👨‍🍳 Подбираю рецепт...")

    try:
        filter_type = context.user_data.get("filter", "")
        recipe = get_recipe(user_text, filter_type)
        context.user_data["filter"] = ""

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Другой рецепт", callback_data=f"again:{user_text[:50]}")]
        ])

        await thinking_msg.delete()
        await update.message.reply_text(recipe, reply_markup=keyboard)

    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await thinking_msg.edit_text("😔 Ошибка. Попробуй ещё раз.")

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data.startswith("again:"):
        products = query.data.replace("again:", "")
        await query.message.reply_text("👨‍🍳 Придумываю другой рецепт...")
        try:
            recipe = get_recipe(products + " (придумай ДРУГОЕ блюдо)")
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Ещё вариант", callback_data=f"again:{products}")]
            ])
            await query.message.reply_text(recipe, reply_markup=keyboard)
        except Exception as e:
            logger.error(f"Ошибка: {e}")
            await query.message.reply_text("😔 Ошибка. Попробуй ещё раз.")

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_products))
    print("✅ Бот запущен!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
