import discord
from discord.ext import commands
from discord.ui import View, Button, Modal, TextInput
import asyncio

TOKEN = ""
GUILD_ID = 1148785310860312676
CATEGORY_ID = 1350199258019532882
SUPPORT_ROLE_IDS = [1321084653397872661]

user_ticket_map = {}  # Mappa utente -> canale
channel_user_map = {}  # Mappa canale -> utente

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

class TicketView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(Button(label="Richiedi supporto", style=discord.ButtonStyle.primary, custom_id="support_button"))

@bot.event
async def on_ready():
    print(f"✅ {bot.user} è online.")
    synced = await bot.tree.sync()
    print(f"🔁 Slash commands sincronizzati: {len(synced)}")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    # DM da utente → canale
    if isinstance(message.channel, discord.DMChannel):
        if message.author.id in user_ticket_map:
            channel = bot.get_channel(user_ticket_map[message.author.id])
            if channel:
                await channel.send(f"📩 **{message.author.name}**: {message.content}")
        else:
            await message.channel.send("❗ Non hai un ticket attivo. Premi il bottone nel server per aprirne uno.")
    # Messaggio da supporto → utente via DM
    elif message.channel.id in channel_user_map and any(role.id in SUPPORT_ROLE_IDS for role in message.author.roles):
        user_id = channel_user_map[message.channel.id]
        user = await bot.fetch_user(user_id)
        try:
            await user.send(f"🎧 **Supporto**: {message.content}")
        except:
            await message.channel.send("⚠️ Impossibile inviare DM all'utente.")

    await bot.process_commands(message)

@bot.command()
@commands.has_permissions(administrator=True)
async def setup(ctx):
    embed = discord.Embed(
        title="🎫 Assistenza",
        description="Hai bisogno di supporto? Premi il bottone qui sotto per aprire un ticket.",
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed, view=TicketView())

@bot.event
async def on_interaction(interaction):
    if interaction.type == discord.InteractionType.component and interaction.data["custom_id"] == "support_button":
        guild = bot.get_guild(GUILD_ID)
        category = guild.get_channel(CATEGORY_ID)

        channel_name = f"ticket-{interaction.user.name}".replace(" ", "-").lower()

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False)
        }

        for role_id in SUPPORT_ROLE_IDS:
            role = guild.get_role(role_id)
            if role:
                overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        channel = await guild.create_text_channel(channel_name, overwrites=overwrites, category=category)

        user_ticket_map[interaction.user.id] = channel.id
        channel_user_map[channel.id] = interaction.user.id

        await interaction.response.send_message("✅ Ticket creato! Controlla i tuoi DM.", ephemeral=True)

        try:
            await interaction.user.send(f"👋 Hai aperto un ticket su **{guild.name}**.\nScrivi qui il tuo messaggio.")
        except:
            await channel.send("⚠️ Non riesco ad inviare un DM all'utente.")

        await channel.send(
            embed=discord.Embed(
                title="🎟️ Ticket Aperto",
                description=f"Ticket aperto da {interaction.user.mention}. Le sue risposte appariranno qui.",
                color=discord.Color.green()
            ),
            view=CloseTicketView(interaction.user)
        )

class CloseTicketView(View):
    def __init__(self, user):
        super().__init__(timeout=None)
        self.user = user
        self.add_item(Button(label="🔒 Chiudi", style=discord.ButtonStyle.danger, custom_id=f"close_ticket_{user.id}"))
        self.add_item(Button(label="📝 Chiudi con motivo", style=discord.ButtonStyle.secondary, custom_id=f"close_with_reason_{user.id}"))

    @discord.ui.button(label="🔒 Chiudi", style=discord.ButtonStyle.danger)
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not any(role.id in SUPPORT_ROLE_IDS for role in interaction.user.roles):
            await interaction.response.send_message("❌ Non hai i permessi per farlo.", ephemeral=True)
            return
        user_id = channel_user_map.get(interaction.channel.id)
        if user_id:
            user = await bot.fetch_user(user_id)
            try:
                await user.send("✅ Il tuo ticket è stato chiuso.")
            except:
                pass
        await interaction.channel.delete()

    @discord.ui.button(label="📝 Chiudi con motivo", style=discord.ButtonStyle.secondary)
    async def close_with_reason(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not any(role.id in SUPPORT_ROLE_IDS for role in interaction.user.roles):
            await interaction.response.send_message("❌ Non hai i permessi per farlo.", ephemeral=True)
            return
        user_id = channel_user_map.get(interaction.channel.id)
        if user_id:
            modal = ReasonModal(user_id)
            await interaction.response.send_modal(modal)

class ReasonModal(Modal, title="Chiudi con motivo"):
    reason = TextInput(label="Motivo", placeholder="Spiega brevemente il motivo", required=True)

    def __init__(self, user_id):
        super().__init__()
        self.user_id = user_id

    async def on_submit(self, interaction: discord.Interaction):
        user = await bot.fetch_user(self.user_id)
        try:
            await user.send(f"❌ Il tuo ticket è stato chiuso.\n**Motivo:** {self.reason.value}")
        except:
            pass
        await interaction.channel.delete()

bot.run(TOKEN)
