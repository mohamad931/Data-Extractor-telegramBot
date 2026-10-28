import os
import json
import re
from datetime import datetime
import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from docx import Document
import io

TOKEN = "9206351203:AAE5JEzuQpceV-CY9VGuQAZ4FI5llZYV5dI"
ADMIN_USERNAME = "Moham7790"
DATA_FILE = "users_data.json"

bot = Bot(token=TOKEN)
dp = Dispatcher()


def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


def read_from_text(file_bytes):
    try:
        return file_bytes.decode("utf-8", errors="ignore")
    except Exception:
        return ""


def read_from_docx(file_io):
    try:
        doc = Document(file_io)
        return "\n".join([p.text for p in doc.paragraphs])
    except Exception:
        return ""


def Regex_list(text):
    emails = list(set(re.findall(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", text)))

    phones = list(
        set(re.findall(r"\b(?:\+?[0-9]{1,3}[-.\s]?)?\(?[0-9]{2,4}\)?[-.\s]?[0-9]{3,4}[-.\s]?[0-9]{3,4}\b", text)))

    filtered_phones = []
    for p in phones:
        digits_only = re.sub(r"\D", "", p)
        if 7 <= len(digits_only) <= 15 and not digits_only.startswith("20"):
            filtered_phones.append(p)

    ips = list(set(re.findall(r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b", text)))

    results = {}
    if emails:
        results["Emails"] = emails
    if filtered_phones:
        results["Phone Numbers"] = filtered_phones
    if ips:
        results["IP Addresses"] = ips
    return results


@dp.message(Command("start"))
async def cmd_start(message: Message):
    user_id = str(message.from_user.id)
    data = load_data()

    if user_id not in data:
        data[user_id] = {
            "attempts": 3,
            "subscription_expiry": None
        }
        save_data(data)

    await message.answer(
        "Welcome to the Professional Data Extractor Bot!\n\n"
        "Send me any .txt or .docx file and I will extract numbers, emails, and IPs instantly.\n\n"
        "You have 3 free attempts to try the bot!"
    )


@dp.message(F.document)
async def handle_docs(message: Message):
    user_id = str(message.from_user.id)
    data = load_data()

    if user_id not in data:
        data[user_id] = {
            "attempts": 3,
            "subscription_expiry": None
        }

    user_info = data[user_id]
    today_date = datetime.now().date()
    is_subscribed = False

    expiry_str = user_info.get("subscription_expiry")
    if expiry_str:
        try:
            expiry_date = datetime.strptime(expiry_str, "%Y-%m-%d").date()
            if today_date <= expiry_date:
                is_subscribed = True
        except ValueError:
            pass

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Subscribe via USDT ($5/Month)",
                    url=f"https://t.me/{ADMIN_USERNAME}"
                )
            ]
        ]
    )

    if not is_subscribed:
        attempts = user_info.get("attempts", 0)
        if attempts <= 0:
            await message.answer(
                "You have exhausted your 3 free attempts!\n\n"
                "To subscribe for unlimited access ($5 USDT / Month), please send the fee using BNB Smart Chain network to:\n\n"
                "0x5A4ad274356105a1E51761e6d5320C624211a0Ae\n\n"
                f"After transferring, send a screenshot of the transaction to @{ADMIN_USERNAME} to activate your account.",
                reply_markup=keyboard
            )
            return

        user_info["attempts"] = attempts - 1
        save_data(data)
        notice = f"\n\n(You have {user_info['attempts']} free attempts remaining)"
    else:
        notice = "\n\n(Active Monthly Subscriber - Unlimited)"

    document = message.document
    file_name = document.file_name.lower()

    if not (file_name.endswith(".txt") or file_name.endswith(".docx")):
        await message.answer("Please send only .txt or .docx files.")
        return

    await message.answer("Processing your file...")

    try:
        file_info = await bot.get_file(document.file_id)
        file_bytes_io = await bot.download_file(file_info.file_path)
        file_bytes = file_bytes_io.read()

        content = ""
        if file_name.endswith(".txt"):
            content = read_from_text(file_bytes)
        elif file_name.endswith(".docx"):
            content = read_from_docx(io.BytesIO(file_bytes))

        if not content.strip():
            await message.answer("The file is empty or could not be read.")
            return

        extracted_data = Regex_list(content)

        if not extracted_data:
            await message.answer("No matching data found." + notice)
            return

        response_text = "Extracted Results:\n\n"
        for key, values in extracted_data.items():
            response_text += f"{key} ({len(values)}):\n"
            response_text += "\n".join(values[:50]) + "\n\n"

        response_text += notice
        await message.answer(response_text)

    except Exception as e:
        print(f"Error: {e}")
        await message.answer("An error occurred while processing the file.")


async def main():
    print("Bot is running...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())