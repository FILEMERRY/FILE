import discord
import os
import asyncio
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv  # ใช้เพื่อโหลดค่าจากไฟล์ .env
from datetime import datetime

# โหลดค่าจากไฟล์ .env
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")  # BOT_TOKEN คือ Token ของบอทจาก Discord Developer Portal
GUILD_ID = int(os.getenv("GUILD_ID"))  # GUILD_ID คือ ID ของเซิร์ฟเวอร์ที่บอทจะทำงาน
CATEGORY_ID = int(os.getenv("CATEGORY_ID"))  # CATEGORY_ID คือ ID ของหมวดหมู่ที่ช่อง Ticket จะถูกสร้าง
ADMIN_ROLE_ID = int(os.getenv("ADMIN_ROLE_ID"))  # ADMIN_ROLE_ID คือ ID ของบทบาทแอดมินในเซิร์ฟเวอร์
TICKET_CHANNEL_ID = int(os.getenv("TICKET_CHANNEL_ID"))  # TICKET_CHANNEL_ID คือ ID ของช่องที่บอทจะส่งปุ่มเพื่อเปิด Ticket
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID"))  # LOG_CHANNEL_ID คือ ID ของช่องที่บอทจะบันทึก log เกี่ยวกับการเปิด Ticket
IMAGE_URL = "https://cdn.discordapp.com/attachments/1367337018782257234/1369431621350195240/giphy.gif?ex=681bd615&is=681a8495&hm=ac27bbf8090878d8cd1a636a4b2162bd882b865d96d449040c5a746c294617cd&"  # URL ของรูปภาพที่จะแสดงในบางที่

intents = discord.Intents.default()  # กำหนด intents ของบอท
bot = commands.Bot(command_prefix="!", intents=intents)  # สร้างบอทที่ใช้ command prefix เป็น '!' และ intent ที่กำหนด

# 🎟️ ปุ่มเปิด Ticket
class TicketButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)  # ตั้งเวลาให้ View ไม่มีการหมดเวลา

    @discord.ui.button(label="เปิด Ticket", style=discord.ButtonStyle.primary, emoji="🎟️")  # ปุ่มสำหรับเปิด Ticket
    async def open_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild  # เซิร์ฟเวอร์ที่ผู้ใช้ส่งคำสั่ง
        category = discord.utils.get(guild.categories, id=CATEGORY_ID)  # ดึงหมวดหมู่ที่ต้องการสร้างช่อง Ticket
        admin_role = guild.get_role(ADMIN_ROLE_ID)  # ดึงบทบาทแอดมินจาก ID
# ตั้งชื่อห้อง ticket ตามชื่อของผู้ใช้
        channel_name = "ticket-{user.name}".lower().replace(" ", "-")[:32]        

        # เช็คว่าผู้ใช้มี Ticket อยู่แล้วหรือไม่
        existing_channel = discord.utils.get(guild.text_channels, name=f"ticket-{interaction.user.name}")
        if existing_channel:
            await interaction.response.send_message(f"คุณมี Ticket อยู่แล้ว: {existing_channel.mention}", ephemeral=True)
            return
        
        # กำหนดการตั้งค่าการอนุญาตในการเข้าถึงช่อง Ticket
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            admin_role: discord.PermissionOverwrite(view_channel=True, send_messages=True),
        }

        # สร้างช่องใหม่สำหรับ Ticket
        ticket_channel = await guild.create_text_channel(
            name=f"ticket-{interaction.user.name}",
            category=category,
            overwrites=overwrites
        )

        # ส่งข้อความแจ้งเตือนในช่อง Ticket พร้อมปุ่มปิด
        await ticket_channel.send(
            f"🎫 **Ticket สำหรับ {interaction.user.mention}**\n🔹 กรุณาระบุปัญหาหรือต้องการอะไร แอดมินจะเข้ามาช่วยเหลือ\n\n"
            f"📢 **แอดมิน**: {admin_role.mention}",  # ใช้ .mention เพื่อแท็กบทบาทแอดมิน
            view=CloseButton()  # แสดงปุ่มปิด Ticket
        )

        # Log การเปิด Ticket
        log_channel = guild.get_channel(LOG_CHANNEL_ID)  # ช่องที่ใช้บันทึก log
        if log_channel:
            embed = discord.Embed(
                title="เปิด Ticket",
                description=f"{interaction.user.mention} ได้เปิด Ticket ใหม่: {ticket_channel.mention}\n"
                            f"📢 **แอดมิน**: {admin_role.mention}",
                color=0x00ff00  # สีเขียว
            )
            embed.set_footer(text=f"เวลา: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
            await log_channel.send(embed=embed)  # ส่ง log ไปที่ช่อง log ที่ไม่ใช่ ephemeral

        # แจ้งผู้ใช้ว่าเปิด Ticket สำเร็จ
        await interaction.response.send_message(f"✅ เปิด Ticket สำเร็จ! {ticket_channel.mention}", ephemeral=True)

# 🔒 ปุ่มปิด Ticket
class CloseButton(discord.ui.View):
    def __init__(self):
        super().__init__()

    @discord.ui.button(label="ปิด Ticket", style=discord.ButtonStyle.danger, emoji="🔒")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        # เช็คว่าเจ้าของเซิร์ฟเวอร์หรือไม่
        if ADMIN_ROLE_ID not in [role.id for role in interaction.user.roles]:
            await interaction.response.send_message("❌ คุณไม่มีสิทธิ์ปิด Ticket นี้", ephemeral=True)
            return
        
        # ดำเนินการ defer ก่อนที่จะแสดงข้อความ
        await interaction.response.defer()

        # สร้างการนับถอยหลัง 5 วินาที
        for i in range(5, 0, -1):
            await interaction.followup.send(content=f"🛑 กำลังปิด Ticket... {i} วินาที", ephemeral=True)
            await asyncio.sleep(1)
        
        # ปิด ticket
        await interaction.channel.delete()

# 🚀 เมื่อบอทออนไลน์ให้ลงทะเบียนคำสั่ง Slash
@bot.event
async def on_ready():
    print(f"✅ {bot.user} ออนไลน์แล้ว!")
    
    # ลงทะเบียน Slash commands
    await bot.tree.sync()

    # ส่งปุ่ม Ticket ไปยังห้องที่กำหนด
    guild = bot.get_guild(GUILD_ID)
    channel = guild.get_channel(TICKET_CHANNEL_ID)  # ห้องที่กำหนด
    if channel:
        embed = discord.Embed(
            title="เปิด Ticket",
            description=( 
                "🎟️ **--------------- TICKET FILEMERRY DESIGN ---------------**\n"
                "🔹 สามารถกดปุ่มด้านล่างเพื่อเปิด Ticket ได้เลยน่ะครับ\n\n"
            ),
            color=0xff0000
  # สีเเดง
        )
        embed.set_thumbnail(url="https://media.discordapp.net/attachments/1347846781500788826/1347846908177285210/logo.png")  # โลโก้ด้านบน
        embed.set_image(url=IMAGE_URL)  # รูปด้านล่าง

        await channel.send(embed=embed, view=TicketButton())  # ส่งปุ่มไปยังห้องที่กำหนด

# สร้างคำสั่ง Slash /openticket ที่เลือกผู้ใช้
@bot.tree.command(name="openticket", description="เปิด Ticket สำหรับผู้ใช้")
@app_commands.describe(user="ผู้ใช้ที่ต้องการเปิด Ticket")
async def openticket(interaction: discord.Interaction, user: discord.Member):
    # เช็คว่าผู้ใช้มีสิทธิ์ในการเปิด Ticket สำหรับผู้อื่น
    if ADMIN_ROLE_ID not in [role.id for role in interaction.user.roles]:
        await interaction.response.send_message("❌ คุณไม่มีสิทธิ์เปิด Ticket สำหรับผู้อื่น", ephemeral=True)
        return

    # เปิด Ticket สำหรับผู้ใช้ที่เลือก
    guild = interaction.guild
    category = discord.utils.get(guild.categories, id=CATEGORY_ID)
    admin_role = guild.get_role(ADMIN_ROLE_ID)  # ดึงบทบาทแอดมินจาก ID

    # เช็คว่าผู้ใช้ที่เลือกมี Ticket อยู่แล้วหรือไม่
    existing_channel = discord.utils.get(guild.text_channels, name=f"ticket-{user.name}")
    if existing_channel:
        await interaction.response.send_message(f"{user.mention} มี Ticket อยู่แล้ว: {existing_channel.mention}", ephemeral=True)
        return
    
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
        guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True),
        admin_role: discord.PermissionOverwrite(view_channel=True, send_messages=True),
    }
    ticket_channel = await guild.create_text_channel(
        name=f"ticket-{user.name}",
        category=category,
        overwrites=overwrites
    )

    # ส่งข้อความในช่อง Ticket
    await ticket_channel.send(
        f"🎫 **Ticket สำหรับ {user.mention}**\n🔹 กรุณาระบุปัญหาหรือต้องการอะไร แอดมินจะเข้ามาช่วยเหลือ\n\n"
        f"📢 **แอดมิน**: {admin_role.mention}",
        view=CloseButton()
    )

    # Log การเปิด Ticket
    log_channel = guild.get_channel(LOG_CHANNEL_ID)
    if log_channel:
        embed = discord.Embed(
            title="เปิด Ticket",
            description=f"{interaction.user.mention} ได้เปิด Ticket ใหม่ให้ {user.mention}: {ticket_channel.mention}\n"
                        f"📢 **แอดมิน**: {admin_role.mention}",
            color=0xff0000
        )
        embed.set_footer(text=f"เวลา: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        await log_channel.send(embed=embed)

    # แจ้งผู้ใช้ว่าเปิด Ticket สำเร็จ
    await interaction.response.send_message(f"✅ เปิด Ticket สำเร็จให้ {user.mention}! {ticket_channel.mention}", ephemeral=True)


# เริ่มต้นบอท
bot.run(TOKEN)
