import re
import asyncio
import os
from telegram import (
    Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ConversationHandler,
    MessageHandler, filters, ContextTypes
)

# Define states for the conversation
(
    FULL_NAME, CONTACT_INFO, TYPE_FACADE,
    TYPE_COUNTERTOP, KITCHEN_LENGTH, FURNITURE_QUALITY,
    DELIVERY_TIME, GIFT_SELECTION, ADDITIONAL_INFO,
) = range(9)

# Telegram chat ID where the result will be sent
TARGET_CHAT_ID = -4513254687

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the questionnaire with the first question."""
    keyboard = [['Фарбований МДФ', 'Ламіноване ДСП', 'Акриловий МДФ']]
    await update.message.reply_text(
        "Оберіть тип фасаду:",
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True),
    )
    return TYPE_FACADE

async def type_facade(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store facade type and ask for countertop type."""
    if update.message.text not in ['Фарбований МДФ', 'Ламіноване ДСП', 'Акриловий МДФ']:
        await update.message.reply_text("Будь ласка, оберіть один із варіантів.")
        return TYPE_FACADE

    context.user_data['facade_type'] = update.message.text
    keyboard = [['Термопласт', 'Акрилова', 'Кварцова']]
    await update.message.reply_text(
        "Оберіть тип стільниці:",
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True),
    )
    return TYPE_COUNTERTOP

async def type_countertop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store countertop type and ask for kitchen length."""
    if update.message.text not in ['Термопласт', 'Акрилова', 'Кварцова']:
        await update.message.reply_text("Будь ласка, оберіть один із варіантів.")
        return TYPE_COUNTERTOP

    context.user_data['countertop_type'] = update.message.text
    await update.message.reply_text("Введіть кількість погонних метрів кухні (2-20):")
    return KITCHEN_LENGTH

async def kitchen_length(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Validate kitchen length and ask for furniture quality."""
    try:
        length = int(update.message.text)
        if 2 <= length <= 20:
            context.user_data['kitchen_length'] = length
            keyboard = [['Економ', 'Стандарт', 'Преміум']]
            await update.message.reply_text(
                "Оберіть якість фурнітури:",
                reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True),
            )
            return FURNITURE_QUALITY
        else:
            await update.message.reply_text("Будь ласка, введіть значення від 2 до 20.")
            return KITCHEN_LENGTH
    except ValueError:
        await update.message.reply_text("Будь ласка, введіть числове значення.")
        return KITCHEN_LENGTH

async def delivery_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store furniture quality and ask for delivery time."""
    if update.message.text not in ['Економ', 'Стандарт', 'Преміум']:
        await update.message.reply_text("Будь ласка, оберіть один із варіантів.")
        return FURNITURE_QUALITY

    context.user_data['furniture_quality'] = update.message.text
    keyboard = [['Поки цікавлюсь', 'Наступного місяця', 'В цьому місяці']]
    await update.message.reply_text(
        "Коли потрібна кухня:",
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True),
    )
    return DELIVERY_TIME

async def gift_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store delivery time and ask for gift selection."""
    if update.message.text not in ['Поки цікавлюсь', 'Наступного місяця', 'В цьому місяці']:
        await update.message.reply_text("Будь ласка, оберіть один із варіантів.")
        return DELIVERY_TIME

    context.user_data['delivery_time'] = update.message.text

    keyboard = [
        ['Знижка 20%', 'Витяжка', 'Стінова панель'],
        ['Мийка', 'Техніка за спеціальною ціною', 'Стільниця']
    ]
    await update.message.reply_text(
        "Оберіть подарунок:",
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True),
    )
    return GIFT_SELECTION

async def ask_additional_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store gift selection and ask for additional information."""
    # Store the gift selection
    context.user_data['gift_selection'] = update.message.text

    await update.message.reply_text(
        "Напишіть додаткову інформацію або надішліть фото/файл, якщо потрібно. "
        "Коли завершите або, якщо не потрібна додаткова інформація, напишіть '/done'."
    )
    return ADDITIONAL_INFO

async def additional_info_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обрабатываем дополнительную информацию и переходим к вопросу про ФІО."""
    if update.message.text and update.message.text.lower() != "/done":
        additional_info = context.user_data.get('additional_info', '')
        context.user_data['additional_info'] = additional_info + "\n" + update.message.text
        await update.message.reply_text("Додана інформація. Можете надіслати ще або напишіть '/done'.")
        return ADDITIONAL_INFO

    elif update.message.photo or update.message.document:
        file_id = update.message.photo[-1].file_id if update.message.photo else update.message.document.file_id
        context.user_data.setdefault('files', []).append(file_id)
        await update.message.reply_text("Файл додано. Можете надіслати ще або напишіть '/done'.")
        return ADDITIONAL_INFO

    elif update.message.text and update.message.text.lower() == "/done":
        await update.message.reply_text("Будь ласка, напишіть своє ім'я та прізвище:")
        return FULL_NAME

async def ask_full_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Сохраняем ФІО и запрашиваем номер телефона."""
    context.user_data['full_name'] = update.message.text
    contact_button = KeyboardButton("Поділитися номером", request_contact=True)
    reply_markup = ReplyKeyboardMarkup([[contact_button]], one_time_keyboard=True)
    await update.message.reply_text("Надішліть свій номер:", reply_markup=reply_markup)
    return CONTACT_INFO

async def contact_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store contact information, validate it, and send the result."""
    if update.message.contact:
        contact = update.message.contact
        username = update.effective_user.username or contact.first_name
        phone_number = contact.phone_number
    else:
        username = update.effective_user.username or update.effective_user.first_name
        phone_number = update.message.text

    if not (re.fullmatch(r"\d{10}", phone_number) or re.fullmatch(r"\+\d{12}", phone_number)):
        await update.message.reply_text(
            "Невірний формат номера телефону. Будь ласка, введіть номер з 10 цифр або 12 цифр із символом '+'."
        )
        return CONTACT_INFO

    if len(phone_number) == 12 and not phone_number.startswith('+'):
        phone_number = f"+{phone_number}"

    context.user_data['contact_info'] = f"@{username} {phone_number}"

    # Use asyncio.gather to send multiple files in parallel
    if 'files' in context.user_data:
        await asyncio.gather(*[
            context.bot.send_document(chat_id=TARGET_CHAT_ID, document=file_id)
            for file_id in context.user_data['files']
        ])

    # Prepare the questionnaire result
    result = (
        f"Результати анкети:\n\n"
        f"Ім'я та прізвище: {context.user_data.get('full_name', 'Не вказано')}\n"
        f"Контакт: {context.user_data.get('contact_info', 'Не вказано')}\n"
        f"Тип фасаду: {context.user_data.get('facade_type', 'Не вказано')}\n"
        f"Тип стільниці: {context.user_data.get('countertop_type', 'Не вказано')}\n"
        f"Довжина кухні: {context.user_data.get('kitchen_length', 'Не вказано')} м\n"
        f"Якість фурнітури: {context.user_data.get('furniture_quality', 'Не вказано')}\n"
        f"Час доставки: {context.user_data.get('delivery_time', 'Не вказано')}\n"
        f"Обраний подарунок: {context.user_data.get('gift_selection', 'Не обрано')}\n"
        f"Додаткова інформація: {context.user_data.get('additional_info', 'Немає')}\n"
    )

    # Send the result message
    await context.bot.send_message(chat_id=TARGET_CHAT_ID, text=result)

    separator = '-' * 92
    await context.bot.send_message(chat_id=TARGET_CHAT_ID, text=separator)

    await update.message.reply_text(
        "Дякуємо! Ваші відповіді надіслані. Для нової заявки напишіть /start", reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END



def main():
    """Run the bot."""
    TOKEN = os.getenv("7774079908:AAFK0vb5AjTrwwFDoqFmQk6GPByo-HUeklw")
    application = ApplicationBuilder().token("7774079908:AAFK0vb5AjTrwwFDoqFmQk6GPByo-HUeklw").build()


    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            TYPE_FACADE: [MessageHandler(filters.TEXT & ~filters.COMMAND, type_facade)],
            TYPE_COUNTERTOP: [MessageHandler(filters.TEXT & ~filters.COMMAND, type_countertop)],
            KITCHEN_LENGTH: [MessageHandler(filters.TEXT & ~filters.COMMAND, kitchen_length)],
            FURNITURE_QUALITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, delivery_time)],
            DELIVERY_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, gift_selection)],
            GIFT_SELECTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_additional_info)],
            ADDITIONAL_INFO: [
                MessageHandler(filters.TEXT | filters.PHOTO | filters.Document.ALL, additional_info_handler)
            ],
            FULL_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_full_name)],
            CONTACT_INFO: [MessageHandler(filters.CONTACT | filters.TEXT, contact_info)],
        },
        fallbacks=[],
    )


    application.add_handler(conv_handler)
    application.run_polling()

if __name__ == '__main__':
    main()
