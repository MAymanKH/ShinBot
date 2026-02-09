import aiohttp
import urllib.parse
import logging
import re
from pyrogram import Client, types
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from utils.usage import save_usage
from config import HADITH_API_BASE

# Store hadith search results for pagination
hadith_cache = {}

logger = logging.getLogger(__name__)


async def hs_command(client: Client, message: types.Message):
    """
    Search for hadiths using the Dorar API.
    Usage: /hs <search query>
    """
    chat = message.chat
    await save_usage(chat, "hs")
    
    if len(message.command) < 2:
        await message.reply(
            "يرجى إدخال نص البحث.\n"
            "مثال: `/hs الصلاة`\n\n"
            "ملاحظة: أضف الرقم '0' في أي مكان في البحث للحصول على جميع الأحاديث (الضعيفة والصحيحة)."
        )
        return

    # Get the search query (everything after /hs)
    search_query = message.text.split(maxsplit=1)[1]
    
    status_msg = await message.reply("جاري البحث عن الأحاديث...")
    
    logger.info(f"Hadith search initiated by user {message.from_user.id} with query: {search_query}")

    # Check if '0' is in the query to get all grades
    # d[]=1: authenticated by scholars (default), d[]=0: all grades
    grade_filter = "0" if "0" in search_query else "1"
    
    # Remove the '0' from the query if it was used as a filter
    if grade_filter == "0":
        search_query_cleaned = search_query.replace("0", "").strip()
    else:
        search_query_cleaned = search_query
    
    logger.info(f"Cleaned query: {search_query_cleaned}, grade filter: {grade_filter}")

    try:
        # Build the API URL
        params = {
            "value": search_query_cleaned,
            "removehtml": "false",
            "specialist": "true",
            "d[]": grade_filter
        }
        
        url = f"{HADITH_API_BASE}/v1/site/hadith/search?" + urllib.parse.urlencode(params)
        
        logger.info(f"Making API request to: {url}")
        
        # Make the API request
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                logger.info(f"API response status: {response.status}")
                
                if response.status != 200:
                    logger.error(f"API returned error status: {response.status}")
                    await status_msg.edit_text(
                        f"حدث خطأ في الاتصال بالخادم: {response.status}\n"
                        "يرجى المحاولة مرة أخرى لاحقاً."
                    )
                    return
                
                data = await response.json()
                logger.info(f"API returned {len(data.get('data', []))} results")
        
        # Check if we got results
        if not data.get("data") or len(data["data"]) == 0:
            logger.warning("No hadiths found for query")
            await status_msg.edit_text(
                "لم يتم العثور على أحاديث لهذا البحث.\n"
                "حاول استخدام كلمات مفتاحية مختلفة."
            )
            return
        
        # Take the first 15 results
        results = data["data"][:15]
        
        logger.info(f"Processing {len(results)} results")
        
        # Store results in cache for pagination
        cache_key = f"hadith_{message.from_user.id}_{hash(search_query)}"
        hadith_cache[cache_key] = {
            'query': search_query_cleaned,
            'results': results,
            'grade_filter': grade_filter,
            'total_results': len(results)
        }
        
        logger.info(f"Showing first hadith with cache_key: {cache_key}")
        
        # Show first hadith
        await show_hadith_page(status_msg, cache_key, 0)
        
        logger.info("Hadith search completed successfully")
        
    except aiohttp.ClientError as e:
        logger.error(f"Network error in hadith search: {str(e)}", exc_info=True)
        await status_msg.edit_text(
            f"حدث خطأ في الاتصال بالشبكة: {str(e)}\n"
            "يرجى التحقق من اتصال الإنترنت والمحاولة مرة أخرى."
        )
    except Exception as e:
        logger.error(f"Unexpected error in hadith search: {str(e)}", exc_info=True)
        await status_msg.edit_text(
            f"حدث خطأ غير متوقع: {str(e)}\n"
            "يرجى المحاولة مرة أخرى لاحقاً."
        )


async def show_hadith_page(message, cache_key, index):
    """Display a single hadith with navigation buttons."""
    logger.info(f"show_hadith_page called with cache_key: {cache_key}, index: {index}")
    
    if cache_key not in hadith_cache:
        logger.error(f"Cache key not found: {cache_key}")
        await message.edit_text("انتهت صلاحية نتائج البحث. يرجى البحث مرة أخرى باستخدام /hs")
        return
    
    data = hadith_cache[cache_key]
    results = data['results']
    query = data['query']
    total = data['total_results']
    
    logger.info(f"Displaying hadith {index+1} of {total}")
    
    if index < 0 or index >= total:
        logger.warning(f"Invalid index: {index} (total: {total})")
        return
    
    hadith = results[index]
    
    # Format the hadith message
    text = f"**البحث:** `{query}`\n"
    text += f"**النتيجة {index + 1} من {total}**\n"
    text += "━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    # Hadith text (trimmed and HTML tags removed)
    hadith_text = hadith.get('hadith', 'غير متوفر')
    # Remove HTML tags
    hadith_text = re.sub(r'<[^>]+>', '', hadith_text)
    # Remove extra whitespace and trim
    hadith_text = re.sub(r'\s+', ' ', hadith_text).strip()
    text += f"{hadith_text}\n\n"
    
    # Narrator (Rawi)
    if hadith.get('rawi'):
        text += f"**الراوي:** {hadith['rawi']}\n"
    
    # Scholar (Mohdith)
    if hadith.get('mohdith'):
        text += f"**المحدث:** {hadith['mohdith']}\n"
    
    # Book
    if hadith.get('book'):
        text += f"**الكتاب:** {hadith['book']}\n"
    
    # Number/Page
    if hadith.get('numberOrPage'):
        text += f"**المرجع:** {hadith['numberOrPage']}\n"
    
    # Grade (authenticity)
    if hadith.get('grade'):
        text += f"**الدرجة:** {hadith['grade']}\n"
    
    # Explanation of grade
    if hadith.get('explainGrade'):
        text += f"**التوضيح:** {hadith['explainGrade']}\n"
    
    # Create navigation buttons
    buttons = []
    
    # Navigation row
    nav_row = []
    if index > 0:
        nav_row.append(InlineKeyboardButton("السابق", callback_data=f"hadith_nav_{cache_key}_{index-1}"))
    if index < total - 1:
        nav_row.append(InlineKeyboardButton("التالي", callback_data=f"hadith_nav_{cache_key}_{index+1}"))
    
    if nav_row:
        buttons.append(nav_row)
    
    # Additional info buttons if available
    info_row = []
    
    if hadith.get('hasSimilarHadith') and hadith.get('similarHadithDorar'):
        similar_url = hadith.get('similarHadithDorar')
        if similar_url and similar_url != '#' and similar_url.startswith('http'):
            info_row.append(InlineKeyboardButton(
                "أحاديث مشابهة", 
                url=similar_url
            ))
    
    if hadith.get('hasAlternateHadithSahih') and hadith.get('alternateHadithSahihDorar'):
        alt_url = hadith.get('alternateHadithSahihDorar')
        if alt_url and alt_url != '#' and alt_url.startswith('http'):
            info_row.append(InlineKeyboardButton(
                "الحديث الصحيح", 
                url=alt_url
            ))
    
    if hadith.get('hasUsulHadith') and hadith.get('usulHadithDorar'):
        usul_url = hadith.get('usulHadithDorar')
        if usul_url and usul_url != '#' and usul_url.startswith('http'):
            info_row.append(InlineKeyboardButton(
                "أصول الحديث", 
                url=usul_url
            ))
    
    if info_row:
        buttons.append(info_row)
    
    # Sharh (explanation) button if available
    if hadith.get('hasSharhMetadata') and hadith.get('sharhMetadata', {}).get('isContainSharh'):
        sharh_id = hadith.get('sharhMetadata', {}).get('id')
        if sharh_id:
            buttons.append([
                InlineKeyboardButton(
                    "عرض الشرح", 
                    callback_data=f"hadith_sharh_{sharh_id}_{cache_key}_{index}"
                )
            ])
    
    keyboard = InlineKeyboardMarkup(buttons)
    
    try:
        logger.info(f"Attempting to edit message with {len(text)} characters")
        await message.edit_text(text, reply_markup=keyboard)
        logger.info("Message edited successfully")
    except Exception as e:
        logger.error(f"Error editing message: {str(e)}", exc_info=True)
        # If message is too long, truncate hadith text
        if "MESSAGE_TOO_LONG" in str(e) or len(text) > 4000:
            hadith_text = hadith.get('hadith', 'غير متوفر')
            # Remove HTML tags
            hadith_text = re.sub(r'<[^>]+>', '', hadith_text)
            # Remove extra whitespace and trim
            hadith_text = re.sub(r'\s+', ' ', hadith_text).strip()
            if len(hadith_text) > 500:
                hadith_text = hadith_text[:500] + "..."
            
            text = f"**البحث:** `{query}`\n"
            text += f"**النتيجة {index + 1} من {total}**\n"
            text += "━━━━━━━━━━━━━━━━━━\n\n"
            text += f"**الحديث:**\n{hadith_text}\n\n"
            
            if hadith.get('rawi'):
                text += f"**الراوي:** {hadith['rawi']}\n"
            if hadith.get('mohdith'):
                text += f"**المحدث:** {hadith['mohdith']}\n"
            if hadith.get('grade'):
                text += f"**الدرجة:** {hadith['grade']}\n"
            
            text += "\n*[تم اختصار نص الحديث بسبب الطول]*"
            
            await message.edit_text(text, reply_markup=keyboard)


async def handle_hadith_callback(client: Client, callback_query):
    """Handle callback queries for hadith pagination."""
    data = callback_query.data
    
    if data == "hadith_close":
        try:
            await callback_query.message.delete()
        except:
            await callback_query.message.edit_text("تم الإغلاق.")
        await callback_query.answer()
        return
    
    if data.startswith("hadith_sharh_"):
        # Handle sharh (explanation) request
        parts = data.split("_", 4)
        if len(parts) >= 5:
            sharh_id = parts[2]
            cache_key = parts[3]
            current_index = int(parts[4])
            
            await callback_query.answer("جاري جلب الشرح...", show_alert=False)
            
            try:
                # Fetch sharh from API
                url = f"{HADITH_API_BASE}/v1/site/sharh/{sharh_id}"
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                        if response.status == 200:
                            sharh_data = await response.json()
                            sharh_text = sharh_data.get('data', {}).get('sharhMetadata', {}).get('sharh', 'الشرح غير متوفر.')
                            
                            # Send sharh as a new message
                            sharh_msg = f"**شرح الحديث:**\n\n{sharh_text}"
                            
                            # Truncate if too long
                            if len(sharh_msg) > 4000:
                                sharh_msg = sharh_msg[:4000] + "\n\n*[تم اختصار الشرح بسبب الطول]*"
                            
                            await callback_query.message.reply(sharh_msg)
                        else:
                            await callback_query.answer("فشل في جلب الشرح.", show_alert=True)
            except Exception as e:
                await callback_query.answer(f"خطأ: {str(e)}", show_alert=True)
        return
    
    # Handle pagination - fixed to properly extract cache_key
    if data.startswith("hadith_nav_"):
        # Remove the "hadith_nav_" prefix
        rest = data[11:]  # len("hadith_nav_") = 11
        # Split only the last underscore to get index
        parts = rest.rsplit("_", 1)
        if len(parts) == 2:
            cache_key = parts[0]
            try:
                index = int(parts[1])
                await show_hadith_page(callback_query.message, cache_key, index)
                await callback_query.answer()
            except ValueError:
                await callback_query.answer("رقم الصفحة غير صحيح.", show_alert=True)
        else:
            await callback_query.answer("بيانات غير صحيحة.", show_alert=True)
    else:
        await callback_query.answer("بيانات غير صحيحة.", show_alert=True)
