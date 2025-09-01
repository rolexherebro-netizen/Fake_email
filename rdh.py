import os
os.system("pip install telebot")
import requests
import telebot
from telebot import types
import datetime
import random
import string
import json
import time
import threading
from flask import Flask, request
import html

# Bot configuration
BOT_TOKEN = "8394570513:AAH5C-Gu_ipFIGEOeha5AcPFVMSH7QWrPEA"
ADMIN_ID = "8331345905"

bot = telebot.TeleBot(BOT_TOKEN)
user_count = 0

# In-memory storage for emails and messages
user_emails = {}  # {user_id: [{email: "", domain: "", messages: [], deletion_id: ""}]}
email_messages = {}  # {email_address: [messages]}
admin_users = [int(ADMIN_ID)]  # List of admin user IDs
email_ids = {}  # {deletion_id: email_address} for deletion
pending_messages = {}  # {user_id: [{email: "", message: {}}]}
last_checked = {}  # {email_address: timestamp} for tracking last check time

# Temp-Mail.io API for email operations
TEMP_MAIL_API = "https://api.internal.temp-mail.io/api/v3"

def get_available_domains():
    """Get available domains from temp-mail.io"""
    try:
        url = f'{TEMP_MAIL_API}/domains'
        response = requests.get(url)
        domains = response.json().get('domains', [])
        return domains
    except:
        return ["greencafe24.com"]  # Fallback domain

def generate_email():
    """Generate a random email address using temp-mail.io domains"""
    domains = get_available_domains()
    domain = random.choice(domains)
    
    # Generate a random username
    username = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
    
    return f"{username}@{domain}"

def create_temp_email(email_address):
    """Create a temporary email using temp-mail.io API"""
    try:
        url = f'{TEMP_MAIL_API}/email/new'
        data = {'name': email_address.split('@')[0], 'domain': email_address.split('@')[1]}
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.post(url, data=data, headers=headers)
        result = response.json()
        return result.get('email', email_address)
    except:
        return email_address  # Fallback to the generated email

def get_email_messages(email_address):
    """Get messages for a temporary email using temp-mail.io API"""
    try:
        url = f'{TEMP_MAIL_API}/email/{email_address}/messages'
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json'
        }
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            messages = response.json()
            return messages if isinstance(messages, list) else []
        else:
            print(f"API Error for {email_address}: {response.status_code} - {response.text}")
            return []
    except Exception as e:
        print(f"Error fetching messages for {email_address}: {e}")
        return []

def send_admin_notification(message):
    """Send notification to admin"""
    try:
        bot.send_message(ADMIN_ID, message, parse_mode='HTML')
    except:
        pass

def generate_deletion_id():
    """Generate a long deletion ID"""
    return "id_2_del" + ''.join(random.choices(string.ascii_lowercase + string.digits, k=16)) + "deletion"

def split_long_message(text, max_length=4000):
    """Split long messages into parts that don't exceed Telegram's limit"""
    if len(text) <= max_length:
        return [text]
    
    parts = []
    while text:
        if len(text) > max_length:
            # Find the last space within the limit
            split_pos = text.rfind(' ', 0, max_length)
            if split_pos == -1:
                split_pos = max_length
            parts.append(text[:split_pos])
            text = text[split_pos:].lstrip()
        else:
            parts.append(text)
            break
    return parts

def escape_html(text):
    """Escape HTML special characters to prevent parsing errors"""
    if not text:
        return ""
    return html.escape(text)

def format_message(email, msg):
    """Format a message for display"""
    sender = escape_html(msg.get('from', 'Unknown Sender'))
    subject = escape_html(msg.get('subject', 'No Subject'))
    body = escape_html(msg.get('body_text', 'No content'))
    timestamp = msg.get('created_at', datetime.datetime.now().isoformat())
    
    try:
        # Try to parse the timestamp
        if 'T' in timestamp:
            time_obj = datetime.datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            time_str = time_obj.strftime('%Y-%m-%d %H:%M')
        else:
            time_str = timestamp
    except:
        time_str = timestamp
    
    message_text = f"""
<b>📨 New Message for {escape_html(email)}</b>
<b>From:</b> {sender}
<b>Subject:</b> {subject}
<b>Time:</b> {time_str}

{body}
"""
    return message_text

def send_message_to_user(user_id, message_text, email, msg):
    """Send message to user with proper error handling"""
    try:
        # Split long messages
        message_parts = split_long_message(message_text)
        
        for part in message_parts:
            try:
                bot.send_message(user_id, part, parse_mode='HTML')
                time.sleep(1)  # Small delay between messages
                return True
            except Exception as e:
                print(f"Error sending HTML message: {e}")
                # Try sending without HTML formatting
                try:
                    plain_text = f"New message for {email}\nFrom: {msg.get('from', 'Unknown')}\nSubject: {msg.get('subject', 'No Subject')}\n\n{msg.get('body_text', 'No content')[:3000]}"
                    plain_parts = split_long_message(plain_text)
                    for plain_part in plain_parts:
                        bot.send_message(user_id, plain_part)
                        time.sleep(1)
                    return True
                except Exception as e2:
                    print(f"Error sending plain text message: {e2}")
                    return False
    except Exception as e:
        print(f"Error in send_message_to_user: {e}")
        return False
    
    return True

@bot.message_handler(commands=['start'])
def send_welcome(message):
    """Handle the /start command"""
    global user_count
    user_count += 1
    
    user_id = message.chat.id
    user_name = message.from_user.first_name
    username = message.from_user.username
    current_time = datetime.datetime.now()
    
    # Notify admin about new user
    admin_msg = f"""
<b>🌌 New Cosmic Traveler Has Joined!</b>
 ـــــــــــــــــــــــــــــــــــــــ 
 👤<b>Celestial Name:</b> {user_name}
🪐<b>Galactic Handle:</b> @{username} 
🆔<b>Universal ID:</b> <code>{user_id}</code>
🔢<b>Stellar Sequence:</b> #{user_count} 
⏳<b>Interstellar Time:</b> {current_time}

✨ <i>Welcome to the cosmos!</i> 🚀
    """
    send_admin_notification(admin_msg)
    
    welcome_text = f"""
<b>👋 Welcome, {user_name}! 🌟</b>

BOT BY :  [#𝗥𝗔𝗗𝗛𝗘𝗬](t.me/boloradhey)

<b>🚀 Available Commands:</b>

📧 /gen – Generate a new temporary email
✏️ /set [email] – Set a custom email address
🌐 /domains – View all available domains
📋 /id – List all your emails with deletion IDs
🗑️ /del [id] – Delete a specific email by ID
ℹ️ /info – Show your user information
🔄 /force - Check for new messages manually
❓ /help – Show help message

NOTE : BOT AUTOCHECKS THE MAIL SO IT WILL TAKE SOME TIME LIKE 5-6 SECONDS TO SHOW YOU THE RECIEVED MAIL !! 
    """
    
    bot.send_message(user_id, welcome_text, parse_mode='HTML')

@bot.message_handler(commands=['domains'])
def list_domains(message):
    """Handle the /domains command to list all available domains"""
    user_id = message.chat.id
    
    domains = get_available_domains()
    
    if not domains:
        bot.send_message(user_id, "❌ Could not retrieve domains at this time. Please try again later.")
        return
    
    domains_text = "<b>📧 Available Domains:</b>\n\n"
    for i, domain in enumerate(domains, 1):
        domains_text += f"{i}. {domain}\n"
    
    domains_text += "\nUse /gen to generate a random email or /set to create a custom one."
    
    bot.send_message(user_id, domains_text, parse_mode='HTML')

@bot.message_handler(commands=['gen'])
def generate_email_command(message):
    """Handle the /gen command to generate a new email"""
    user_id = message.chat.id
    user_name = message.from_user.first_name
    
    # Generate email
    email = generate_email()
    
    # Try to create it with temp-mail.io
    temp_email = create_temp_email(email)
    
    # Generate unique long ID for deletion
    deletion_id = generate_deletion_id()
    email_ids[deletion_id] = temp_email
    
    # Initialize user_emails if not exists
    if user_id not in user_emails:
        user_emails[user_id] = []
    
    # Store the email for this user
    email_data = {
        'email': temp_email,
        'messages': [],
        'created_at': datetime.datetime.now().isoformat(),
        'deletion_id': deletion_id
    }
    user_emails[user_id].append(email_data)
    
    # Initialize message storage for this email
    if temp_email not in email_messages:
        email_messages[temp_email] = []
    
    # Initialize last checked time
    last_checked[temp_email] = datetime.datetime.now()
    
    bot.send_message(
        user_id, 
        f"<b>✅ Your temporary email address has been created:</b>\n\n<code>{temp_email}</code>\n\n"
        f"<b>Deletion ID:</b> <code>{deletion_id}</code>\n\n"
        f"You can use it anywhere you will get response in bot only !!",
        parse_mode='HTML'
    )

@bot.message_handler(commands=['set'])
def set_email_command(message):
    """Handle the /set command to set a custom email"""
    user_id = message.chat.id
    
    # Check if user provided an email
    if len(message.text.split()) < 2:
        bot.send_message(user_id, "Please provide an email address after the /set command. Example: /set radhey@radhey.com")
        return
    
    custom_email = message.text.split()[1].strip()
    
    # Validate email format
    if '@' not in custom_email:
        bot.send_message(user_id, "Invalid email format. Please provide a valid email address.")
        return
    
    # Check if email already exists in any user
    for user_data_list in user_emails.values():
        for email_data in user_data_list:
            if email_data['email'] == custom_email:
                bot.send_message(user_id, "This email is already taken by another user. Please try a different one.")
                return
    
    # Try to create it with temp-mail.io
    temp_email = create_temp_email(custom_email)
    
    # Generate unique long ID for deletion
    deletion_id = generate_deletion_id()
    email_ids[deletion_id] = temp_email
    
    # Initialize user_emails if not exists
    if user_id not in user_emails:
        user_emails[user_id] = []
    
    # Store the email for this user
    email_data = {
        'email': temp_email,
        'messages': [],
        'created_at': datetime.datetime.now().isoformat(),
        'deletion_id': deletion_id
    }
    user_emails[user_id].append(email_data)
    
    # Initialize message storage for this email
    if temp_email not in email_messages:
        email_messages[temp_email] = []
    
    # Initialize last checked time
    last_checked[temp_email] = datetime.datetime.now()
    
    bot.send_message(
        user_id, 
        f"<b>✅ Your custom email address has been created:</b>\n\n<code>{temp_email}</code>\n\n"
        f"<b>Deletion ID:</b> <code>{deletion_id}</code>\n\n"
        f"You can use it anywhere you will get response in bot only !!",
        parse_mode='HTML'
    )

@bot.message_handler(commands=['id'])
def list_emails_command(message):
    """Handle the /id command to list all emails with their deletion IDs"""
    user_id = message.chat.id
    
    # Check if user has any emails
    if user_id not in user_emails or not user_emails[user_id]:
        bot.send_message(user_id, "You don't have any active email addresses. Use /gen to generate one or /set to create a custom one.")
        return
    
    response = "<b>Your email addresses:</b>\n\n"
    for email_data in user_emails[user_id]:
        response += f"<code>{email_data['email']}</code> / <code>{email_data['deletion_id']}</code>\n\n"
    
    response += "Use /del [id] to delete a specific email address."
    
    bot.send_message(user_id, response, parse_mode='HTML')

@bot.message_handler(commands=['del'])
def delete_email_command(message):
    """Handle the /del command to delete a specific email by ID"""
    user_id = message.chat.id
    
    # Check if user provided an ID
    if len(message.text.split()) < 2:
        bot.send_message(user_id, "Please provide an email ID after the /del command. Example: /del id_2_delxyzdeletion\n\nUse /id to see your emails and their IDs.")
        return
    
    deletion_id = message.text.split()[1].strip()
    
    # Check if the ID exists
    if deletion_id not in email_ids:
        bot.send_message(user_id, "Email ID not found. Use /id to see your emails and their IDs.")
        return
    
    email_to_delete = email_ids[deletion_id]
    
    # Verify the email belongs to the user
    email_belongs_to_user = False
    if user_id in user_emails:
        for i, email_data in enumerate(user_emails[user_id]):
            if email_data['email'] == email_to_delete and email_data['deletion_id'] == deletion_id:
                email_belongs_to_user = True
                # Remove the email from user's list
                user_emails[user_id].pop(i)
                if not user_emails[user_id]:  # If no emails left, remove user entry
                    del user_emails[user_id]
                break
    
    if not email_belongs_to_user:
        bot.send_message(user_id, "You don't have permission to delete this email address.")
        return
    
    # Delete the email from storage
    if email_to_delete in email_messages:
        del email_messages[email_to_delete]
    
    if email_to_delete in last_checked:
        del last_checked[email_to_delete]
    
    del email_ids[deletion_id]
    
    bot.send_message(user_id, f"<b>✅ Email address</b> <code>{email_to_delete}</code> <b>has been deleted successfully.</b>", parse_mode='HTML')

@bot.message_handler(commands=['force'])
def force_check_messages(message):
    """Manually check for new messages"""
    user_id = message.chat.id
    
    if user_id not in user_emails or not user_emails[user_id]:
        bot.send_message(user_id, "You don't have any active email addresses. Use /gen to generate one first.")
        return
    
    bot.send_message(user_id, "🔄 Checking for new messages...")
    
    # Check for new messages
    found_new = False
    for email_data in user_emails[user_id]:
        email = email_data['email']
        old_count = len(email_messages.get(email, []))
        
        # Get new messages from API
        new_messages = get_email_messages(email)
        
        if new_messages and len(new_messages) > old_count:
            found_new = True
            # Update stored messages
            email_messages[email] = new_messages
            
            # Show new messages to user
            for msg in new_messages[old_count:]:
                message_text = format_message(email, msg)
                success = send_message_to_user(user_id, message_text, email, msg)
                
                if not success:
                    # Store failed message for later retrieval
                    if user_id not in pending_messages:
                        pending_messages[user_id] = []
                    pending_messages[user_id].append({
                        'email': email,
                        'message': msg
                    })
    
    # Check if there are any pending messages from previous failures
    if user_id in pending_messages and pending_messages[user_id]:
        found_new = True
        bot.send_message(user_id, "📥 Retrieving previously failed messages...")
        
        for pending_msg in pending_messages[user_id]:
            message_text = format_message(pending_msg['email'], pending_msg['message'])
            send_message_to_user(user_id, message_text, pending_msg['email'], pending_msg['message'])
        
        # Clear pending messages after attempting to send them
        pending_messages[user_id] = []
    
    if not found_new:
        bot.send_message(user_id, "No new messages found.")

@bot.message_handler(commands=['stats'])
def admin_stats(message):
    """Show detailed statistics for admin"""
    user_id = message.chat.id
    
    if user_id not in admin_users:
        bot.send_message(user_id, "❌ You are not authorized to use this command.")
        return
    
    # Calculate some stats
    domains = get_available_domains()
    domain_usage = {}
    
    for user_data_list in user_emails.values():
        for email_data in user_data_list:
            domain = email_data['email'].split('@')[1]
            domain_usage[domain] = domain_usage.get(domain, 0) + 1
    
    stats_text = f"""
<b>🌌 Cosmic Statistics Dashboard</b>
ــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــ
👥 <b>Total Space Travelers:</b> {user_count}
📨 <b>Active Cosmic Mailboxes:</b> {sum(len(emails) for emails in user_emails.values())}
📬 <b>Messages in the Void:</b> {sum(len(msgs) for msgs in email_messages.values())}
🌐 <b>Available Galactic Domains:</b> {len(domains)}
ــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــــ
📊 <b>Domain Usage Across the Galaxy:</b>
"""
    
    for domain, count in domain_usage.items():
        stats_text += f"{domain}: {count} accounts\n"
    
    bot.send_message(user_id, stats_text, parse_mode='HTML')

@bot.message_handler(commands=['broadcast'])
def admin_broadcast(message):
    """Broadcast message to all users"""
    user_id = message.chat.id
    
    if user_id not in admin_users:
        bot.send_message(user_id, "❌ You are not authorized to use this command.")
        return
    
    # Extract the broadcast message
    broadcast_msg = message.text.replace('/broadcast', '').strip()
    
    if not broadcast_msg:
        bot.send_message(user_id, "Please provide a message to broadcast. Usage: /broadcast Your message here")
        return
    
    # Get all unique user IDs (from user_emails and any other sources)
    all_user_ids = set(user_emails.keys())
    
    # Send the broadcast message
    success_count = 0
    fail_count = 0
    
    for uid in all_user_ids:
        try:
            bot.send_message(uid, f"<b>📢 Announcement from Admin:</b>\n\n{broadcast_msg}", parse_mode='HTML')
            success_count += 1
        except:
            fail_count += 1
    
    bot.send_message(
        user_id, 
        f"<b>✅ Broadcast completed!</b>\n<b>Success:</b> {success_count}\n<b>Failed:</b> {fail_count}",
        parse_mode='HTML'
    )

@bot.message_handler(commands=['admin'])
def admin_panel(message):
    """Show admin panel"""
    user_id = message.chat.id
    
    if user_id not in admin_users:
        bot.send_message(user_id, "❌ You are not authorized to access the admin panel.")
        return
    
    admin_text = f"""
<b>👑 Cosmic Command Center</b> ━━━━━━━━━━━━━━━━━━━━━

👥 <b>Total Space Travelers:</b> <code>{user_count}</code> 
📨<b>Active Cosmic Mailboxes:</b> <code>{sum(len(emails) for emails in user_emails.values())}</code> 
📬<b>Messages in the Void:</b> <code>{sum(len(msgs) for msgs in email_messages.values())}</code> 
━━━━━━━━━━━━━━━━━━━━━

<b>🛠️ Admin Commands:</b> 
📊/stats – Show detailed cosmic statistics 
📢/broadcast – Send a transmission to all users

🌌 <i>Command the cosmos with wisdom.</i> ✨      """
    
    bot.send_message(user_id, admin_text, parse_mode='HTML')

@bot.message_handler(commands=['help'])
def help_command(message):
    """Handle the /help command"""
    help_text = """
<b>🤖 Temporary Email Bot Help</b>

<b>How to use:</b>
1. Generate a temporary email address using /gen
2. Or set a custom email using /set [email]
3. Use this email address on any website that requires email verification
4. Emails sent to this address will be shown here automatically

<b>Commands:</b>
/start - Show welcome message
/gen - Generate a new temporary email
/set [email] - Set a custom email address
/domains - Get list of all available domains
/id - List all your emails with their deletion IDs
/del [id] - Delete a specific email by ID
/force - Manually check for new messages
/info - Show your user information
/help - Show this help message
    """
    
    bot.send_message(message.chat.id, help_text, parse_mode='HTML')

@bot.message_handler(commands=['info'])
def user_info(message):
    """Show user information"""
    user_id = message.chat.id
    user_name = message.from_user.first_name
    username = message.from_user.username
    current_time = datetime.datetime.now()
    
    info_text = f"""
<b>👤 Your Cosmic ID Card</b>
━━━━━━━━━━━━━━━━━━━━━

👤 <b>Name:</b> {user_name}
📱 <b>Username:</b> @{username}
🆔 <b>User ID:</b> <code>{user_id}</code>
⏰ <b>Time:</b> {current_time}

🌌 <i>Exploring the email galaxy since {current_time}!</i> 🚀
    """
    
    if user_id in user_emails and user_emails[user_id]:
        info_text += f"""
<b>📧 Cosmic Mailboxes</b>
━━━━━━━━━━━━━━━━━━━━━
"""
        for email_data in user_emails[user_id]:
            email = email_data['email']
            created_at = datetime.datetime.fromisoformat(email_data['created_at'])
            deletion_id = email_data.get('deletion_id', 'N/A')
            info_text += f"""
📭 <b>Email:</b> <code>{email}</code>
🗑️ <b>Deletion ID:</b> <code>{deletion_id}</code>
🕒 <b>Created:</b> {created_at.strftime('%Y-%m-%d %H:%M')}
📨 <b>Messages:</b> {len(email_messages.get(email, []))}
━━━━━━━━━━━━━━━━━━━━━
"""
    
    bot.send_message(user_id, info_text, parse_mode='HTML')

# Background task to check for new messages and show them automatically
def check_messages_periodically():
    """Periodically check for new messages for all active emails and show them"""
    while True:
        try:
            print("Checking for new messages...")
            
            # Create a copy to avoid modification during iteration
            user_emails_copy = user_emails.copy()
            
            for user_id, email_data_list in user_emails_copy.items():
                for email_data in email_data_list:
                    email = email_data['email']
                    
                    # Only check emails that haven't been checked in the last 30 seconds
                    current_time = datetime.datetime.now()
                    if email in last_checked:
                        time_since_last_check = (current_time - last_checked[email]).total_seconds()
                        if time_since_last_check < 30:
                            continue
                    
                    old_count = len(email_messages.get(email, []))
                    
                    # Get new messages from API
                    new_messages = get_email_messages(email)
                    
                    if new_messages and len(new_messages) > old_count:
                        print(f"Found {len(new_messages) - old_count} new messages for {email}")
                        
                        # Update stored messages
                        email_messages[email] = new_messages
                        
                        # Show new messages to user
                        for msg in new_messages[old_count:]:
                            message_text = format_message(email, msg)
                            success = send_message_to_user(user_id, message_text, email, msg)
                            
                            if not success:
                                # Store failed message for later retrieval
                                if user_id not in pending_messages:
                                    pending_messages[user_id] = []
                                pending_messages[user_id].append({
                                    'email': email,
                                    'message': msg
                                })
                    
                    # Update last checked time
                    last_checked[email] = current_time
            
            time.sleep(15)  # Check every 15 seconds
            
        except Exception as e:
            print(f"Error in background message checking: {e}")
            time.sleep(30)  # Wait longer if there's an error

# Start background message checking
message_thread = threading.Thread(target=check_messages_periodically, daemon=True)
message_thread.start()

if __name__ == "__main__":
    print("Bot is starting...")
    bot.infinity_polling()
