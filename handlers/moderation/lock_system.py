import logging
from pyrogram import Client, types
from pyrogram.errors import ChatAdminRequired
from utils.decorators import admin_only
from utils.usage import save_usage
from utils.helpers import get_markdown_mention

logger = logging.getLogger(__name__)

@admin_only
async def lock_command(client: Client, message: types.Message):
    """Lock the chat - prevent all members from sending messages"""
    chat = message.chat
    await save_usage(chat, "lock")
    
    # Check if it's a group chat
    if chat.type == "private":
        await message.reply("❌ This command can only be used in group chats.")
        return
    
    try:
        # Get current chat permissions
        chat_info = await client.get_chat(chat.id)
        
        # Check if chat is already locked
        if (hasattr(chat_info, 'permissions') and chat_info.permissions and 
            not chat_info.permissions.can_send_messages):
            await message.reply("🔒 Chat is already locked.")
            return
        
        # Lock the chat by removing all default permissions
        locked_permissions = types.ChatPermissions(
            can_send_messages=False,
            can_send_media_messages=False,
            can_send_polls=False,
        )
        
        await client.set_chat_permissions(chat.id, locked_permissions)
        
        await message.reply(
            f"🔒 **Chat Locked**\n\n"
            f"Only administrators can send messages now.\n"
            f"**Locked by:** {get_markdown_mention(message.from_user)}\n\n"
            f"Use `/unlock` to restore normal chat permissions.",
            disable_web_page_preview=True
        )
        
        logger.info(f"Chat {chat.id} locked by admin {message.from_user.id}")
        
    except ChatAdminRequired:
        await message.reply("❌ I need admin privileges with 'Change chat info' permission to lock the chat.")
    except Exception as e:
        await message.reply(f"❌ Error locking chat: {str(e)}")
        logger.error(f"Error in lock command: {e}")

@admin_only
async def unlock_command(client: Client, message: types.Message):
    """Unlock the chat - restore normal permissions for all members"""
    chat = message.chat
    await save_usage(chat, "unlock")
    
    # Check if it's a group chat
    if chat.type == "private":
        await message.reply("❌ This command can only be used in group chats.")
        return
    
    try:
        # Get current chat permissions
        chat_info = await client.get_chat(chat.id)
        
        # Check if chat is already unlocked
        if (hasattr(chat_info, 'permissions') and chat_info.permissions and 
            chat_info.permissions.can_send_messages):
            await message.reply("🔓 Chat is already unlocked.")
            return
        
        # Unlock the chat by restoring default permissions
        unlocked_permissions = types.ChatPermissions(
            can_send_messages=True,
            can_send_media_messages=True,
            can_send_polls=True,
        )
        
        await client.set_chat_permissions(chat.id, unlocked_permissions)
        
        await message.reply(
            f"🔓 **Chat Unlocked**\n\n"
            f"All members can send messages again.\n"
            f"**Unlocked by:** {get_markdown_mention(message.from_user)}\n\n"
            f"Normal chat permissions have been restored.",
            disable_web_page_preview=True
        )
        
        logger.info(f"Chat {chat.id} unlocked by admin {message.from_user.id}")
        
    except ChatAdminRequired:
        await message.reply("❌ I need admin privileges with 'Change chat info' permission to unlock the chat.")
    except Exception as e:
        await message.reply(f"❌ Error unlocking chat: {str(e)}")
        logger.error(f"Error in unlock command: {e}")
