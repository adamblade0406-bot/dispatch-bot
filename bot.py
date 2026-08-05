import os
import pdfplumber
from google import genai
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_KEY")

client = genai.Client(api_key=GEMINI_KEY)

SYSTEM_PROMPT = """
You are a dispatch extraction assistant. Extract details from the provided Rate Confirmation text and output ONLY text in the EXACT format below:

✅✅✅NEXT LOAD✅✅✅
Load# [LOAD_NUMBER]
BOL#: [BOL_NUMBER]
============================
PU: [DATE] [TIME]
[FACILITY_NAME]
[ADDRESS]
============================
DEL: [DATE] [TIME]
[FACILITY_NAME]
[ADDRESS]
============================
Deadhead: [DH_MILES] miles
Loaded: [LOADED_MILES] miles
Total: [TOTAL_MILES] miles
============================
Please ensure that the Trailer photos, Bill of Lading (BOL), seal information, and all other relevant documents are sent to dispatch and confirmed prior to departure from the facility.
Failure to confirm these documents before departure may result in additional charges.
Late arrivals and departures, non-compliance with dispatch instructions, and refusal of a load after booking may also incur charges.
Please ensure that your tracking system is consistently activated. Any charges incurred from the broker due to the app not being used will be the responsibility of the driver.

Rules:
- Fill in actual values inside brackets based on the document.
- Do NOT add bullet points, extra text, or commentary.
- If deadhead miles aren't specified in document, write "0 miles" or estimate based on given info.
"""

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Send me a Rate Confirmation PDF, and I will format the load details for you!")

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("Processing Rate Confirmation...")
    doc = update.message.document
    
    file = await context.bot.get_file(doc.file_id)
    file_path = f"temp_{doc.file_name}"
    await file.download_to_drive(file_path)

    extracted_text = ""
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            extracted_text += (page.extract_text() or "") + "\n"
            
    if os.path.exists(file_path):
        os.remove(file_path)

    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=f"{SYSTEM_PROMPT}\n\nHere is the document text:\n{extracted_text}"
    )

    formatted_dispatch = response.text
    await msg.edit_text(f"```text\n{formatted_dispatch}\n```", parse_mode="Markdown")

if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    
    print("Bot running...")
    app.run_polling()
