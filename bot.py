- 👋 Hi, I’m @imcsxbby

import discord
from discord import app_commands
from discord.ext import commands
import requests
from datetime import datetime, timezone, timedelta

# Jeton du bot Discord et clé API Sellpass
DISCORD_BOT_TOKEN = ''
SELLPASS_API_KEY = ''
SHOP_ID = ''  # Remplacez par votre Shop ID réel

# Initialisation du bot avec intents pour les commandes slash
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='/', intents=intents)

# Fonction pour traduire les statuts
def translate_status(status_code):
    # Mapping vérifié et ajusté pour Sellpass
    status_mapping = {
        0: "🆕 New",
        1: "❌ Cancelled",  # Vérifiez si 1 correspond bien à ❌ Cancelled dans votre API
        2: "⌛ Expired",
        3: "✅ Completed",  # Assurez-vous que 3 correspond bien à ✅ Completed
    }
    return status_mapping.get(status_code, "⌛ Expired")



# Fonction pour formater la date et ajuster le fuseau horaire
def format_date(date_str):
    try:
        date_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        date_obj = date_obj.astimezone(timezone(timedelta(hours=2)))  # Ajustez le fuseau horaire ici
        return date_obj.strftime('%d %b %Y %H:%M')
    except Exception as e:
        print(f"Erreur lors du formatage de la date : {e}")
        return "Non disponible"

class InvoiceView(discord.ui.View):
    def __init__(self, invoices, per_page=10):
        super().__init__()
        self.invoices = sorted(invoices, key=lambda x: x.get('created_at', ''), reverse=True)  # Trier par date décroissante
        self.per_page = per_page
        self.page = 0

    def create_embed(self):
        """Crée un embed stylisé pour afficher les factures."""
        start = self.page * self.per_page
        end = start + self.per_page
        page_invoices = self.invoices[start:end]

        embed = discord.Embed(
            title=f"📜 Factures - Page {self.page + 1}/{(len(self.invoices) - 1) // self.per_page + 1}",
            color=discord.Color.dark_blue(),
            description="📊 Affiche les dernières transactions effectuées."
        )

        for invoice in page_invoices:
            email = invoice.get('customerInfo', {}).get('customerForShop', {}).get('customer', {}).get('email', 'Non disponible')
            valeur = invoice.get('endPrice', 'Non disponible')
            statut = translate_status(invoice.get('status', 1))  # Valeur par défaut ajustée à "Completed" pour les statuts incohérents
            temps = format_date(invoice.get('timeline', [{}])[-1].get('time', 'Non disponible'))
            transaction_id = invoice.get('id', 'Non disponible')
            produit = invoice.get('partInvoices', [{}])[0].get('product', {}).get('title', 'Non disponible')

            embed.add_field(
                name=f"📦 {produit}",
                value=(
                    f"📧 **Email :** {email}\n"
                    f"💰 **Valeur :** {valeur} EUR\n"
                    f"📋 **Statut :** {statut}\n"
                    f"🕒 **Date :** {temps}\n"
                    f"🔑 **Transaction ID :** `{transaction_id}`"
                ),
                inline=False
            )

        embed.set_footer(text="Utilisez les boutons ci-dessous pour naviguer entre les pages.")
        return embed

    @discord.ui.button(label='⬅️ Précédent', style=discord.ButtonStyle.secondary)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Gérer le bouton de page précédente."""
        if self.page > 0:
            self.page -= 1
            await interaction.response.edit_message(embed=self.create_embed())

    @discord.ui.button(label='Suivant ➡️', style=discord.ButtonStyle.secondary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Gérer le bouton de page suivante."""
        if self.page < (len(self.invoices) - 1) // self.per_page:
            self.page += 1
            await interaction.response.edit_message(embed=self.create_embed())

class MyBot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def fetch_orders(self):
        """Récupère les factures depuis l'API Sellpass."""
        print("Tentative de récupération des factures depuis l'API Sellpass...")
        url = f"https://dev.sellpass.io/self/{SHOP_ID}/invoices"
        headers = {
            'Authorization': f'Bearer {SELLPASS_API_KEY}',
            'Content-Type': 'application/json'
        }
        try:
            print(f"Envoi d'une requête GET à {url} avec les en-têtes {headers}")
            response = requests.get(url, headers=headers)
            print(f"Réponse reçue avec le code de statut : {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                invoices = data.get('data', [])
                for invoice in invoices:
                    print(invoice)  # Affiche chaque facture pour voir la structure réelle
                print(f"{len(invoices)} factures récupérées avec succès.")
                return invoices
            else:
                print(f"Erreur lors de la récupération des factures : {response.status_code} - {response.text}")
                return []
        except Exception as e:
            print(f"Une exception s'est produite lors de la récupération des factures : {e}")
            return []

    @app_commands.command(name="orders", description="Affiche toutes les factures depuis Sellpass.")
    @app_commands.checks.has_role(1278857164076748801)  # ID du rôle requis pour exécuter la commande
    async def orders(self, interaction: discord.Interaction):
        """Commande slash pour afficher toutes les factures depuis l'API Sellpass."""
        print("Commande slash /orders invoquée.")
        commandes = self.fetch_orders()
        if commandes:
            print("Affichage des factures avec pagination.")
            view = InvoiceView(commandes)
            await interaction.response.send_message(embed=view.create_embed(), view=view)
        else:
            print("Aucune facture trouvée, envoi du message approprié sur Discord.")
            await interaction.response.send_message("**🚫 Aucune facture trouvée.**")

    @orders.error
    async def orders_error(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.MissingRole):
            await interaction.response.send_message("🚫 Vous n'avez pas les permissions nécessaires pour exécuter cette commande.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(MyBot(bot))

@bot.event
async def on_ready():
    print("Bot prêt. Tentative de synchronisation des commandes slash avec Discord.")
    await setup(bot)
    try:
        await bot.tree.sync()
        print("Commandes slash synchronisées avec succès.")
    except Exception as e:
        print(f"Erreur lors de la synchronisation des commandes : {e}")

# Lancer le bot
print("Démarrage du bot...")
bot.run(DISCORD_BOT_TOKEN)
