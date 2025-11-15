import math
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.types import Message, BufferedInputFile
from aiogram.client.default import DefaultBotProperties
from aiogram import F
from io import BytesIO
import asyncio
import os


# BOT TOKEN (from Render Environment Variable)
TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# User session data
sessions = {}


# =============================
# START COMMAND
# =============================
@dp.message(commands={"start"})
async def start(message: Message):
    await message.answer(
        "Welcome!\n\n"
        "Two ways to use the bot:\n\n"
        "1️⃣ FAST MODE:\n"
        "/convert <contacts_per_file> <prefix> <start_number>\n"
        "Example:\n"
        "/convert 50 TOXIC 100\n\n"
        "2️⃣ INTERACTIVE MODE:\n"
        "Type /convert only:\n"
        "/convert\n\n"
        "Interactive sequence (your choice - Option 3):\n"
        "1. Prefix\n"
        "2. Contacts per file\n"
        "3. Starting number\n"
        "4. Send TXT file\n"
        "5. Number of VCF files"
    )


# =============================
# "/convert" COMMAND HANDLING
# =============================
@dp.message(commands={"convert"})
async def convert(message: Message):

    parts = message.text.split()

    # If user typed only /convert → interactive mode
    if len(parts) == 1:
        sessions[message.from_user.id] = {"stage": "ask_prefix"}
        await message.answer("Enter prefix name:")
        return

    # Fast mode
    try:
        _, qty, prefix, start = parts
        qty = int(qty)
        start = int(start)
    except:
        await message.answer("❌ Correct format:\n/convert <contacts_per_file> <prefix> <start_number>")
        return

    sessions[message.from_user.id] = {
        "qty": qty,
        "prefix": prefix,
        "start": start,
        "stage": "wait_txt"
    }

    await message.answer("Now send your TXT file.")


# =============================
# INTERACTIVE MODE (TEXT INPUT)
# =============================
@dp.message(F.text)
async def interactive(message: Message):

    user = message.from_user.id
    if user not in sessions:
        return

    stage = sessions[user].get("stage")

    # 1️⃣ Ask prefix
    if stage == "ask_prefix":
        sessions[user]["prefix"] = message.text.strip()
        sessions[user]["stage"] = "ask_qty"
        await message.answer("How many contacts per VCF file?")
        return

    # 2️⃣ Ask quantity per file
    if stage == "ask_qty":
        if not message.text.isdigit():
            await message.answer("Enter a number.")
            return
        sessions[user]["qty"] = int(message.text)
        sessions[user]["stage"] = "ask_start"
        await message.answer("Enter starting number:")
        return

    # 3️⃣ Ask starting number
    if stage == "ask_start":
        if not message.text.isdigit():
            await message.answer("Enter a number.")
            return
        sessions[user]["start"] = int(message.text)
        sessions[user]["stage"] = "wait_txt"
        await message.answer("Now upload your TXT file.")
        return

    # 5️⃣ Receive number of VCF files
    if stage == "wait_file_count":
        if not message.text.isdigit():
            await message.answer("Enter a valid number.")
            return

        file_count = int(message.text)

        if file_count < 1 or file_count > 100:
            await message.answer("Maximum allowed: 100")
            return

        await create_vcf_files(message, file_count)
        return


# =============================
# TXT FILE HANDLING
# =============================
@dp.message(F.document)
async def handle_txt(message: Message):

    user = message.from_user.id
    if user not in sessions or sessions[user]["stage"] != "wait_txt":
        await message.answer("Run /convert first.")
        return

    if not message.document.file_name.endswith(".txt"):
        await message.answer("Send a valid TXT file.")
        return

    # Download file
    file = await bot.get_file(message.document.file_id)
    file_data = await bot.download_file(file.file_path)
    content = file_data.read().decode(errors="ignore").splitlines()

    numbers = [x.strip() for x in content if x.strip()]
    sessions[user]["numbers"] = numbers
    sessions[user]["stage"] = "wait_file_count"

    await message.answer("How many VCF files do you want?\n(example: 5)\nMaximum: 100")


# =============================
# CREATE VCF FILES
# =============================
async def create_vcf_files(message: Message, file_count: int):

    user = message.from_user.id
    data = sessions[user]

    qty = data["qty"]
    prefix = data["prefix"]
    start = data["start"]
    numbers = data["numbers"]

    total_required = qty * file_count

    if len(numbers) < total_required:
        await message.answer(
            f"❌ Not enough phone numbers in TXT.\n"
            f"Required: {total_required}\n"
            f"Available: {len(numbers)}"
        )
        return

    # Use only needed numbers
    numbers = numbers[:total_required]

    await message.answer(
        f"Processing {file_count} file(s) × {qty} contacts each = {total_required} contacts..."
    )

    pointer = 0
    counter = start

    for i in range(file_count):

        chunk = numbers[pointer: pointer + qty]
        pointer += qty

        vcf_txt = ""

        for num in chunk:
            vcf_txt += (
                "BEGIN:VCARD\n"
                "VERSION:3.0\n"
                f"FN:{prefix} {counter}\n"
                f"TEL:{num}\n"
                "END:VCARD\n"
            )
            counter += 1

        buffer = BytesIO(vcf_txt.encode())

        await message.answer_document(
            BufferedInputFile(buffer.read(), filename=f"{prefix}_{i+1}.vcf")
        )

    sessions.pop(user, None)  # clear session


# =============================
# START BOT
# =============================
async def main():
    print("Bot is running...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
  
