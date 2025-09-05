import discord
from discord.ext import commands
import os
import asyncio
import re

# Configuration des modes et salons
# Comment remplir la configuration MODES :
# - "video": liste des IDs des salons où seules les vidéos (pièces jointes + liens) sont autorisées
# - "photo": liste des IDs des salons où seules les images (pièces jointes) sont autorisées  
# - "feed": liste des IDs des salons où texte, GIFs et audio sont autorisés
# Exemple : MODES = {"video": [1234567890, 9876543210], "photo": [1111111111], "feed": [2222222222, 3333333333]}

MODES = {
    "video": [
        # Ajoutez ici les IDs des salons vidéo-only
        # Exemple: 123456789012345678
    ],
    "photo": [
        # Ajoutez ici les IDs des salons photo-only
        # Exemple: 987654321098765432
    ],
    "feed": [
        # Ajoutez ici les IDs des salons feed (texte/gifs/audio)
        # Exemple: 555666777888999000
    ]
}

# Configuration
INTENTS = discord.Intents.default()
INTENTS.message_content = True
INTENTS.guilds = True

# Extensions de fichiers par type
VIDEO_EXTENSIONS = ['.mp4', '.mov', '.avi', '.mkv', '.webm', '.m4v', '.wmv', '.flv', '.3gp', '.ogv']
PHOTO_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg', '.tiff']
AUDIO_EXTENSIONS = ['.mp3', '.wav', '.ogg', '.m4a', '.flac', '.aac', '.wma']

# Regex pour détecter les liens HTTP/HTTPS
URL_PATTERN = re.compile(r'https?://[^\s]+', re.IGNORECASE)

# Créer l'instance du bot
bot = commands.Bot(command_prefix='!', intents=INTENTS)

@bot.event
async def on_ready():
    print(f'{bot.user} est connecté à Discord!')
    print(f'Bot connecté à {len(bot.guilds)} serveur(s)')
    for guild in bot.guilds:
        print(f'- {guild.name} (ID: {guild.id})')

def get_channel_mode(channel_id):
    """Retourne le mode du salon ('video', 'photo', 'feed') ou None si non configuré"""
    for mode, channel_ids in MODES.items():
        if channel_id in channel_ids:
            return mode
    return None

def has_valid_content(message, mode):
    """Vérifie si le message a un contenu valide selon le mode du salon"""
    if mode == "video":
        # Mode vidéo : accepter pièces jointes vidéo OU liens
        has_video_attachment = any(
            attachment.filename.lower().endswith(tuple(VIDEO_EXTENSIONS))
            for attachment in message.attachments
        )
        has_url = bool(URL_PATTERN.search(message.content))
        return has_video_attachment or has_url
    
    elif mode == "photo":
        # Mode photo : accepter seulement les pièces jointes images
        return any(
            attachment.filename.lower().endswith(tuple(PHOTO_EXTENSIONS))
            for attachment in message.attachments
        )
    
    elif mode == "feed":
        # Mode feed : accepter texte, GIFs et audio (tout sauf vidéos)
        has_text = bool(message.content.strip())
        has_gif = any(
            attachment.filename.lower().endswith('.gif')
            for attachment in message.attachments
        )
        has_audio = any(
            attachment.filename.lower().endswith(tuple(AUDIO_EXTENSIONS))
            for attachment in message.attachments
        )
        # Rejeter si c'est uniquement une vidéo
        has_only_video = (
            len(message.attachments) > 0 and
            all(attachment.filename.lower().endswith(tuple(VIDEO_EXTENSIONS))
                for attachment in message.attachments) and
            not has_text
        )
        return (has_text or has_gif or has_audio) and not has_only_video
    
    return True

@bot.event
async def on_message(message):
    # Ignorer les messages du bot lui-même
    if message.author == bot.user:
        return
    
    # Vérifier si le salon est configuré
    channel_mode = get_channel_mode(message.channel.id)
    if not channel_mode:
        # Salon non configuré, laisser passer
        await bot.process_commands(message)
        return
    
    # Vérifier si le contenu est valide pour ce mode
    if not has_valid_content(message, channel_mode):
        try:
            # Envoyer un message d'avertissement temporaire
            mode_names = {
                'video': '🎥 vidéos',
                'photo': '📸 images',
                'feed': '📝 texte, GIFs et audio'
            }
            
            warning_msg = await message.channel.send(
                f"⚠️ {message.author.mention}, ce salon accepte uniquement {mode_names.get(channel_mode, 'le contenu autorisé')}.",
                delete_after=5
            )
            
            # Supprimer le message non conforme
            await message.delete()
            
            # Log de l'action
            print(f"Message supprimé de {message.author} dans #{message.channel.name} (mode: {channel_mode})")
            
        except discord.errors.Forbidden:
            print(f"Permissions insuffisantes pour supprimer le message dans #{message.channel.name}")
        except Exception as e:
            print(f"Erreur lors de la suppression du message: {e}")
    
    # Continuer le traitement des commandes
    await bot.process_commands(message)

@bot.command(name='status')
async def status_command(ctx):
    """Affiche le statut du bot et la configuration des salons"""
    embed = discord.Embed(title="Status du VideoModerator Bot", color=0x00ff00)
    embed.add_field(name="Statut", value="🟢 En ligne", inline=True)
    embed.add_field(name="Serveurs", value=len(bot.guilds), inline=True)
    
    # Afficher la configuration des modes
    for mode, channel_ids in MODES.items():
        if channel_ids:
            channel_names = []
            for channel_id in channel_ids:
                channel = bot.get_channel(channel_id)
                if channel:
                    channel_names.append(f"#{channel.name}")
                else:
                    channel_names.append(f"ID: {channel_id}")
            
            mode_display = {
                'video': '🎥 Salons Vidéo',
                'photo': '📸 Salons Photo', 
                'feed': '📝 Salons Feed'
            }
            
            embed.add_field(
                name=mode_display.get(mode, mode.title()),
                value="\n".join(channel_names) if channel_names else "Aucun salon configuré",
                inline=False
            )
    
    await ctx.send(embed=embed)

@bot.command(name='help_config')
async def help_config_command(ctx):
    """Affiche l'aide pour configurer les salons"""
    embed = discord.Embed(title="Configuration des Salons", color=0x0099ff)
    embed.description = "Pour configurer les salons, modifiez la variable MODES dans le code :"
    
    embed.add_field(
        name="🎥 Mode Video",
        value="Accepte uniquement les vidéos (fichiers + liens)\nExemple: `\"video\": [123456789]`",
        inline=False
    )
    
    embed.add_field(
        name="📸 Mode Photo", 
        value="Accepte uniquement les images\nExemple: `\"photo\": [987654321]`",
        inline=False
    )
    
    embed.add_field(
        name="📝 Mode Feed",
        value="Accepte le texte, GIFs et audio\nExemple: `\"feed\": [555666777]`",
        inline=False
    )
    
    await ctx.send(embed=embed)

# Démarrer le bot
if __name__ == "__main__":
    TOKEN = os.getenv('DISCORD_BOT_TOKEN')
    if not TOKEN:
        print("Erreur: DISCORD_BOT_TOKEN n'est pas défini dans les variables d'environnement")
    else:
        bot.run(TOKEN)
