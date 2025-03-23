import discord
from discord.ext import commands
import logging
import os
import sys
from sqlalchemy import create_engine, func, Column, Integer, String, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
import random
from datetime import datetime
import asyncio
from dotenv import load_dotenv
from discord import app_commands
from flask import Flask
import threading

# Flask app initialization
app = Flask(__name__)

@app.route('/')
def home():
    return 'Bot is running!'

# Load .env file
load_dotenv()

# Logging settings
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Discord Bot Token
TOKEN = os.getenv('DISCORD_TOKEN')
if not TOKEN:
    print("Hata: DISCORD_TOKEN bulunamadı!")
    sys.exit(1)

# Admin user IDs (Discord user IDs)
ADMIN_USER_IDS = [1154754197057703946]  # Discord user IDs here

# SQLAlchemy setup
Base = declarative_base()
engine = create_engine('sqlite:///siralama.db')
Session = sessionmaker(bind=engine)

# Model definitions
class Urun(Base):
    __tablename__ = 'urun'
    id = Column(Integer, primary_key=True)
    urun_adi = Column(String(100), nullable=False)

class Kullanici(Base):
    __tablename__ = 'kullanici'
    id = Column(Integer, primary_key=True)
    kullanici_adi = Column(String(100), nullable=False, unique=True)
    discord_id = Column(String(100), nullable=False, unique=True)

class Siralama(Base):
    __tablename__ = 'siralama'
    id = Column(Integer, primary_key=True)
    urun_id = Column(Integer, ForeignKey('urun.id'), nullable=False)
    kullanici_id = Column(Integer, ForeignKey('kullanici.id'), nullable=False)
    sira_no = Column(Integer, nullable=False)
    urun = relationship('Urun', backref='siralamalar')
    kullanici = relationship('Kullanici', backref='siralamalar')

# Veritabanı tabloları oluştur
Base.metadata.create_all(engine)

# Bot ayarları
class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(command_prefix='/', intents=intents)

    async def setup_hook(self):
        try:
            await self.tree.sync()
            print("Commands synced successfully!")
        except Exception as e:
            print(f"Error syncing commands: {e}")

bot = MyBot()

def is_admin():
    async def predicate(interaction: discord.Interaction):
        return interaction.user.id in ADMIN_USER_IDS
    return app_commands.check(predicate)

@bot.event
async def on_ready():
    logger.info(f'Logged in as {bot.user}!')
    try:
        await bot.tree.sync()
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} commands:")
        for command in bot.tree.get_commands():
            print(f"- /{command.name}: {command.description}")
    except Exception as e:
        print(f"Error syncing commands: {e}")
    await bot.change_presence(activity=discord.Game(name="Type /help"))

@bot.tree.command(name="help", description="Lists all bot commands")
async def help(interaction: discord.Interaction):
    """Lists all bot commands"""
    is_user_admin = interaction.user.id in ADMIN_USER_IDS

    base_commands = (
        '⚔️ **BlackHorse Guild Loot System**\n\n'
        '📋 **General Commands:**\n'
        '➖➖➖➖➖➖➖➖➖➖➖➖\n'
        '📊 **/itemlist** - View all item priority lists\n'
        '🎯 **/itemqueue** - View priority list for specific item\n'
        '👤 **/myloot** - View all your item priorities\n'
        '🎲 **/roll** - Roll the dice (1-100)\n'
        '🎉 **/raffle** - Random selection among guildies\n'
    )

    admin_commands = (
        '\n👑 **Guild Master Commands:**\n'
        '➖➖➖➖➖➖➖➖➖➖➖➖\n'
        '📊 **/moveplayer** - Change player\'s position in queue\n'
        '❌ **/pass** - Player passes on item\n'
        '✅ **/bind** - Bind item to player (moves to end of queue)\n'
        '➕ **/additem** - Add new item to track\n'
        '❌ **/deleteitem** - Delete item\n'
        '👤 **/addplayer** - Add new guild member\n'
        '❌ **/kickplayer** - Remove guild member\n\n'
        '💡 **Note:** These commands can only be used by Guild Masters and Officers.'
    )

    message = base_commands + (admin_commands if is_user_admin else '')
    await interaction.response.send_message(message)

@bot.tree.command(name="itemlist", description="Shows all item priority lists")
async def itemlist(interaction: discord.Interaction):
    """Shows all item priority lists"""
    await interaction.response.defer()
    
    session = Session()
    try:
        products = session.query(Urun).all()
        if not products:
            await interaction.followup.send("📦 No items added yet!")
            return

        mesaj = "```ansi\n"
        mesaj += "\u001b[1;35m⚔️ BLACKHORSE GUILD - ITEM PRIORITY ⚔️\u001b[0m\n"
        mesaj += "\u001b[1;35m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\u001b[0m\n\n"
        
        for product in products:
            rankings = session.query(Siralama, Kullanici).join(Kullanici).filter(
                Siralama.urun_id == product.id
            ).order_by(Siralama.sira_no).all()

            mesaj += f"\u001b[1;33m🎯 {product.urun_adi.upper()}\u001b[0m\n"
            
            if not rankings:
                mesaj += "\u001b[0;37m   • No priority list yet!\u001b[0m\n"
            else:
                for siralama, kullanici in rankings:
                    if siralama.sira_no == 1:
                        renk = "\u001b[1;33m"  # Gold
                        sembol = "👑"
                    elif siralama.sira_no == 2:
                        renk = "\u001b[1;37m"  # Silver
                        sembol = "🥈"
                    elif siralama.sira_no == 3:
                        renk = "\u001b[0;33m"  # Bronze
                        sembol = "🥉"
                    else:
                        renk = "\u001b[0;37m"  # Normal
                        sembol = "•"
                    
                    kullanici_adi = kullanici.kullanici_adi[:15]
                    if len(kullanici.kullanici_adi) > 15:
                        kullanici_adi += "..."
                    
                    sira_no = f"{siralama.sira_no:2d}"
                    mesaj += f"{renk}   {sembol} {sira_no}. {kullanici_adi}\u001b[0m\n"
            
            mesaj += "\n"

        mesaj += "```"
        
        while mesaj:
            if len(mesaj) <= 1990:
                await interaction.followup.send(mesaj)
                break
            else:
                son_index = mesaj[:1990].rindex("\n")
                parcali_mesaj = mesaj[:son_index] + "```"
                await interaction.followup.send(parcali_mesaj)
                mesaj = "```ansi\n" + mesaj[son_index+1:]

    except Exception as e:
        await interaction.followup.send(f"❌ An error occurred: {str(e)}")
    finally:
        session.close()

@bot.tree.command(name="itemqueue", description="Shows priority list for specific loot")
async def itemqueue(interaction: discord.Interaction, item_name: str):
    """Shows priority list for specific loot"""
    session = Session()
    try:
        product = session.query(Urun).filter(Urun.urun_adi.ilike(f"%{item_name}%")).first()
        if not product:
            await interaction.response.send_message(f"❌ Loot item '{item_name}' not found!")
            return

        rankings = session.query(Siralama, Kullanici).join(Kullanici).filter(
            Siralama.urun_id == product.id
        ).order_by(Siralama.sira_no).all()

        if not rankings:
            await interaction.response.send_message(f"📝 No priority list yet for **{product.urun_adi}**!")
            return

        mesaj = "```ansi\n"
        mesaj += f"\u001b[1;35m🎯 {product.urun_adi.upper()} LOOT PRIORITY LIST\u001b[0m\n"
        mesaj += "\u001b[1;35m━━━━━━━━━━━━━━━━━━━━━━\u001b[0m\n\n"

        for siralama, kullanici in rankings:
            if siralama.sira_no == 1:
                renk = "\u001b[1;33m"  # Gold
                sembol = "👑"
            elif siralama.sira_no == 2:
                renk = "\u001b[1;37m"  # Silver
                sembol = "🥈"
            elif siralama.sira_no == 3:
                renk = "\u001b[0;33m"  # Bronze
                sembol = "🥉"
            else:
                renk = "\u001b[0;37m"  # Normal
                sembol = "•"
            
            kullanici_adi = kullanici.kullanici_adi[:15]
            if len(kullanici.kullanici_adi) > 15:
                kullanici_adi += "..."
            
            sira_no = f"{siralama.sira_no:2d}"
            mesaj += f"{renk}   {sembol} {sira_no}. {kullanici_adi}\u001b[0m\n"

        mesaj += "```"
        await interaction.response.send_message(mesaj)
    finally:
        session.close()

@bot.tree.command(name="roll", description="Roll the dice (1-100)")
async def roll(interaction: discord.Interaction):
    """Roll the dice (1-100)"""
    roll_result = random.randint(1, 100)
    await interaction.response.send_message(f"🎲 **{interaction.user.display_name}** rolled: **{roll_result}**!")

@bot.tree.command(name="raffle", description="Random selection among guildies")
async def raffle(interaction: discord.Interaction):
    """Random selection among guildies"""
    session = Session()
    try:
        kullanicilar = session.query(Kullanici).all()
        if not kullanicilar:
            await interaction.response.send_message("Not enough users for raffle!")
            return

        kazanan = random.choice(kullanicilar)
        await interaction.response.send_message(f"🎉 Raffle Result: **{kazanan.kullanici_adi}** won!")
    finally:
        session.close()

@bot.tree.command(name="moveplayer", description="Change player's position in queue (Guild Master only)")
@app_commands.check(lambda interaction: interaction.user.id in ADMIN_USER_IDS)
async def moveplayer(interaction: discord.Interaction, item_name: str, member: discord.Member, new_position: int):
    """Change player's position in queue (Guild Master only)"""
    session = Session()
    try:
        urun = session.query(Urun).filter(Urun.urun_adi.ilike(f"%{item_name}%")).first()
        if not urun:
            await interaction.response.send_message(f"❌ Item '{item_name}' not found!")
            return

        kullanici = session.query(Kullanici).filter(
            Kullanici.discord_id == str(member.id)
        ).first()
        if not kullanici:
            await interaction.response.send_message(f"❌ Player '{member.display_name}' not found in the guild roster!")
            return

        mevcut_siralama = session.query(Siralama).filter_by(
            kullanici_id=kullanici.id,
            urun_id=urun.id
        ).first()

        max_sira = session.query(func.count(Siralama.id)).filter(
            Siralama.urun_id == urun.id
        ).scalar()

        if new_position < 1 or new_position > max_sira:
            await interaction.response.send_message(f"❌ Position must be between 1 and {max_sira}!")
            return

        if mevcut_siralama:
            eski_sira = mevcut_siralama.sira_no
            session.delete(mevcut_siralama)
            
            session.query(Siralama).filter(
                Siralama.urun_id == urun.id,
                Siralama.sira_no > eski_sira
            ).update({Siralama.sira_no: Siralama.sira_no - 1})
            
            session.query(Siralama).filter(
                Siralama.urun_id == urun.id,
                Siralama.sira_no >= new_position
            ).update({Siralama.sira_no: Siralama.sira_no + 1})
        else:
            session.query(Siralama).filter(
                Siralama.urun_id == urun.id,
                Siralama.sira_no >= new_position
            ).update({Siralama.sira_no: Siralama.sira_no + 1})

        yeni_siralama = Siralama(
            kullanici_id=kullanici.id,
            urun_id=urun.id,
            sira_no=new_position
        )
        session.add(yeni_siralama)

        session.commit()
        await interaction.response.send_message(f"✅ **{kullanici.kullanici_adi}**'s position for **{urun.urun_adi}** has been updated to {new_position}!")
    except Exception as e:
        session.rollback()
        await interaction.response.send_message(f"❌ Error updating position: {str(e)}")
    finally:
        session.close()

@bot.tree.command(name="pass", description="Player passes on loot (Guild Master only)")
@app_commands.check(lambda interaction: interaction.user.id in ADMIN_USER_IDS)
async def pass_loot(interaction: discord.Interaction, item_name: str, member: discord.Member):
    """Player passes on loot (Guild Master only)"""
    session = Session()
    try:
        urun = session.query(Urun).filter(Urun.urun_adi.ilike(f"%{item_name}%")).first()
        if not urun:
            await interaction.response.send_message(f"❌ Loot item '{item_name}' not found!")
            return

        kullanici = session.query(Kullanici).filter(
            Kullanici.discord_id == str(member.id)
        ).first()
        if not kullanici:
            await interaction.response.send_message(f"❌ Player '{member.display_name}' not found in the guild roster!")
            return

        siralama = session.query(Siralama).filter_by(
            kullanici_id=kullanici.id,
            urun_id=urun.id
        ).first()

        if siralama:
            eski_sira = siralama.sira_no
            session.delete(siralama)
            
            session.query(Siralama).filter(
                Siralama.urun_id == urun.id,
                Siralama.sira_no > eski_sira
            ).update({Siralama.sira_no: Siralama.sira_no - 1})
            
            session.commit()
            await interaction.response.send_message(f"✅ **{kullanici.kullanici_adi}** passed on **{urun.urun_adi}**!")
        else:
            await interaction.response.send_message(f"**{kullanici.kullanici_adi}** is not in the priority list for **{urun.urun_adi}**!")
    except Exception as e:
        session.rollback()
        await interaction.response.send_message(f"❌ An error occurred: {str(e)}")
    finally:
        session.close()

@bot.tree.command(name="additem", description="Adds a new item to track (Guild Master only)")
@app_commands.check(lambda interaction: interaction.user.id in ADMIN_USER_IDS)
async def additem(interaction: discord.Interaction, item_name: str):
    """Adds a new item to track (Guild Master only)"""
    session = Session()
    try:
        existing_item = session.query(Urun).filter(
            Urun.urun_adi.ilike(f"%{item_name}%")
        ).first()
        
        if existing_item:
            await interaction.response.send_message(
                f"❌ This item already exists! ({existing_item.urun_adi})",
                ephemeral=True
            )
            return

        urun = Urun(urun_adi=item_name)
        session.add(urun)
        session.commit()

        kullanicilar = session.query(Kullanici).all()
        admin_kullanicilar = [k for k in kullanicilar if int(k.discord_id) in ADMIN_USER_IDS]
        normal_kullanicilar = [k for k in kullanicilar if int(k.discord_id) not in ADMIN_USER_IDS]
        
        random.shuffle(normal_kullanicilar)
        siralanmis_kullanicilar = admin_kullanicilar + normal_kullanicilar

        for sira, kullanici in enumerate(siralanmis_kullanicilar, 1):
            yeni_siralama = Siralama(
                kullanici_id=kullanici.id,
                urun_id=urun.id,
                sira_no=sira
            )
            session.add(yeni_siralama)

        session.commit()
        
        siralama_text = f"✅ **{item_name}** has been successfully added!\n\nAutomatic priority list:\n"
        for sira, kullanici in enumerate(siralanmis_kullanicilar, 1):
            siralama_text += f"{sira}. {kullanici.kullanici_adi}\n"
        
        await interaction.response.send_message(siralama_text)
    except Exception as e:
        session.rollback()
        await interaction.response.send_message(
            f"❌ Error adding item: {str(e)}",
            ephemeral=True
        )
    finally:
        session.close()

@bot.tree.command(name="bind", description="Binds an item to a player and moves them to end of queue (Guild Master only)")
@app_commands.check(lambda interaction: interaction.user.id in ADMIN_USER_IDS)
async def bind(interaction: discord.Interaction, item_name: str, member: discord.Member):
    """Binds an item to a player and moves them to end of queue (Guild Master only)"""
    session = Session()
    try:
        product = session.query(Urun).filter(Urun.urun_adi.ilike(f"%{item_name}%")).first()
        if not product:
            await interaction.response.send_message(f"❌ Item '{item_name}' not found!")
            return

        user = session.query(Kullanici).filter(
            Kullanici.discord_id == str(member.id)
        ).first()
        if not user:
            await interaction.response.send_message(f"❌ Player '{member.display_name}' not found in the guild roster!")
            return

        current_ranking = session.query(Siralama).filter_by(
            kullanici_id=user.id,
            urun_id=product.id
        ).first()

        if not current_ranking:
            await interaction.response.send_message(f"❌ Player '{member.display_name}' is not in the priority list for '{item_name}'!")
            return

        max_rank = session.query(func.count(Siralama.id)).filter(
            Siralama.urun_id == product.id
        ).scalar()

        old_rank = current_ranking.sira_no
        
        session.query(Siralama).filter(
            Siralama.urun_id == product.id,
            Siralama.sira_no > old_rank
        ).update({Siralama.sira_no: Siralama.sira_no - 1})

        current_ranking.sira_no = max_rank
            
        session.commit()
        await interaction.response.send_message(
            f"✅ **{member.display_name}** has bound **{product.urun_adi}** and moved to the end of the queue!"
        )
    except Exception as e:
        session.rollback()
        await interaction.response.send_message(f"❌ An error occurred: {str(e)}")
    finally:
        session.close()

@bot.tree.command(name="deleteitem", description="Deletes an item (Guild Master only)")
@app_commands.check(lambda interaction: interaction.user.id in ADMIN_USER_IDS)
async def deleteitem(interaction: discord.Interaction, item_name: str):
    """Deletes an item (Guild Master only)"""
    session = Session()
    try:
        urun = session.query(Urun).filter(Urun.urun_adi.ilike(f"%{item_name}%")).first()
        if not urun:
            await interaction.response.send_message(f"❌ Item '{item_name}' not found!")
            return

        # First delete all rankings associated with this item
        session.query(Siralama).filter(Siralama.urun_id == urun.id).delete()
        
        # Then delete the item itself
        session.delete(urun)
        session.commit()
        await interaction.response.send_message(f"✅ **{urun.urun_adi}** has been successfully deleted!")
    except Exception as e:
        session.rollback()
        await interaction.response.send_message(f"❌ Error deleting item: {str(e)}")
    finally:
        session.close()

@bot.tree.command(name="addplayer", description="Adds a new guild member (Guild Master only)")
@app_commands.check(lambda interaction: interaction.user.id in ADMIN_USER_IDS)
async def addplayer(interaction: discord.Interaction, member: discord.Member, username: str = None):
    """Adds a new guild member (Guild Master only)"""
    if username is None:
        username = member.display_name

    session = Session()
    try:
        existing_user = session.query(Kullanici).filter(
            (Kullanici.kullanici_adi == username) | 
            (Kullanici.discord_id == str(member.id))
        ).first()
        
        if existing_user:
            await interaction.response.send_message(
                f"❌ This player is already in the guild! (ID: {existing_user.discord_id}, Name: {existing_user.kullanici_adi})",
                ephemeral=True
            )
            return

        kullanici = Kullanici(
            kullanici_adi=username,
            discord_id=str(member.id)
        )
        session.add(kullanici)
        session.commit()

        urunler = session.query(Urun).all()
        for urun in urunler:
            son_sira = session.query(func.max(Siralama.sira_no)).filter(
                Siralama.urun_id == urun.id
            ).scalar()
            
            yeni_sira = (son_sira or 0) + 1
            yeni_siralama = Siralama(
                kullanici_id=kullanici.id,
                urun_id=urun.id,
                sira_no=yeni_sira
            )
            session.add(yeni_siralama)
        
        session.commit()
        await interaction.response.send_message(
            f"✅ **{username}** has been successfully added and placed in all item queues!"
        )
    except Exception as e:
        session.rollback()
        await interaction.response.send_message(
            f"❌ Error adding player: {str(e)}",
            ephemeral=True
        )
    finally:
        session.close()

@bot.tree.command(name="kickplayer", description="Removes a guild member (Guild Master only)")
@app_commands.check(lambda interaction: interaction.user.id in ADMIN_USER_IDS)
async def kickplayer(interaction: discord.Interaction, member: discord.Member):
    """Removes a guild member (Guild Master only)"""
    session = Session()
    try:
        kullanici = session.query(Kullanici).filter(
            Kullanici.discord_id == str(member.id)
        ).first()
        if not kullanici:
            await interaction.response.send_message(f"❌ Player '{member.display_name}' not found in the guild roster!")
            return

        # First delete all rankings associated with this player
        session.query(Siralama).filter(Siralama.kullanici_id == kullanici.id).delete()
        
        # Then delete the player
        session.delete(kullanici)
        session.commit()

        # After deleting the player, update rankings for all items
        urunler = session.query(Urun).all()
        for urun in urunler:
            # Get all rankings for this item
            siralamalar = session.query(Siralama).filter(
                Siralama.urun_id == urun.id
            ).order_by(Siralama.sira_no).all()
            
            # Update rankings to be sequential
            for index, siralama in enumerate(siralamalar, 1):
                siralama.sira_no = index
        
        session.commit()
        await interaction.response.send_message(f"✅ **{kullanici.kullanici_adi}** has been successfully removed from the guild!")
    except Exception as e:
        session.rollback()
        await interaction.response.send_message(f"❌ Error removing player: {str(e)}")
    finally:
        session.close()

# Error handling
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    try:
        if isinstance(error, app_commands.CheckFailure):
            await interaction.response.send_message("❌ You don't have permission to use this command!", ephemeral=True)
        else:
            if not interaction.response.is_done():
                await interaction.response.send_message(f"❌ An error occurred: {str(error)}", ephemeral=True)
            else:
                await interaction.followup.send(f"❌ An error occurred: {str(error)}", ephemeral=True)
            logger.error(f"Error: {str(error)}")
    except discord.errors.NotFound:
        pass  # Ignore if interaction has already timed out

def run_bot():
    bot.run(TOKEN)

if __name__ == '__main__':
    # Create database tables
    Base.metadata.create_all(engine)
    
    # Start the bot in a separate thread
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.start()
    
    # Start Flask app
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port) 