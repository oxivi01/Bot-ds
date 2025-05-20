import discord
from discord.ext import commands
from discord.ui import Button, View, Select
import asyncio
from keep_alive import keep_alive


intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.guilds = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)

GUILD_ID = 1373680335002402886
CATEGORY_RL_VOICE_ID = 1374068129172426803
CATEGORY_FN_VOICE_ID = 1374068135447232633

CHANNEL_CHOIX_JEU_ID = 1374068121098256405
CHANNEL_TOURNOI_MODERATION_ID = 1374068203118006272

CHANNEL_TOURNOIS_RL_ANNONCE_ID = 1374068130996813924
CHANNEL_TOURNOIS_FN_ANNONCE_ID = 1374068138437640213

ROLE_ADMIN_ID = 1374068094158377042
ROLE_MODO_ID = 1374068095500554470

ROLE_RL_ID = 1374068096477691915
ROLE_FN_ID = 1374068097107103882  # Remplacé par un vrai ID

RL_RANKS = {
    "Bronze": 1374068098935820411,
    "Silver": 1374068099678212138,
    "Gold": 1374068100907139092,
    "Platine": 1374068102509232278,
    "Diamant": 1374068103373258903,
    "Champion": 1374068104186826766,
    "Grand Champion": 1374068105474474097,
    "Supersonic Legend": 1374076604103397537
}

FN_RANKS = {
    "Bronze": 1374068106908930209,
    "Silver": 1374068107831677059,
    "Gold": 1374068108469473292,
    "Platinum": 1374068109840748546,
    "Diamond": 1374068110851575808,
    "Elite": 1374068111749152800,
    "Champion": 1374068112953184386,
    "Unreal": 1374068113519280210
}

tournois = {}
inscriptions = {}





class JeuSelectView(View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Rocket League",
                       style=discord.ButtonStyle.primary,
                       custom_id="jeu_rl")
    async def rl_button(self, interaction: discord.Interaction,
                        button: Button):
        await interaction.response.defer()
        await send_rank_select(interaction, "Rocket League")

    @discord.ui.button(label="Fortnite",
                       style=discord.ButtonStyle.primary,
                       custom_id="jeu_fn")
    async def fn_button(self, interaction: discord.Interaction,
                        button: Button):
        await interaction.response.defer()
        await send_rank_select(interaction, "Fortnite")


async def send_rank_select(interaction: discord.Interaction, jeu: str):
    ranks = RL_RANKS if jeu == "Rocket League" else FN_RANKS
    options = [
        discord.SelectOption(label=rank, value=rank) for rank in ranks.keys()
    ]

    class RankSelect(Select):

        def __init__(self):
            super().__init__(placeholder=f"Choisis ton rang {jeu}...",
                             min_values=1,
                             max_values=1,
                             options=options)

        async def callback(self, select_interaction: discord.Interaction):
            selected_rank = self.values[0]
            guild = bot.get_guild(GUILD_ID)
            member = await guild.fetch_member(select_interaction.user.id)

            try:
                await member.remove_roles(*[
                    r for r in member.roles
                    if r.id in (list(RL_RANKS.values()) +
                                list(FN_RANKS.values()) +
                                [ROLE_RL_ID, ROLE_FN_ID])
                ])
            except Exception:
                pass

            role_jeu = guild.get_role(ROLE_RL_ID if jeu ==
                                      "Rocket League" else ROLE_FN_ID)
            rank_role = guild.get_role(
                RL_RANKS[selected_rank] if jeu ==
                "Rocket League" else FN_RANKS[selected_rank])

            try:
                await member.add_roles(role_jeu, rank_role)
            except discord.Forbidden:
                await select_interaction.response.send_message(
                    "Je n'ai pas la permission de modifier tes rôles.",
                    ephemeral=True)
                return

            await select_interaction.response.send_message(
                f"Tu as reçu les rôles {role_jeu.name} et {rank_role.name} !",
                ephemeral=True)

    view = View(timeout=60)
    view.add_item(RankSelect())
    await interaction.followup.send(f"Choisis ton rang pour {jeu} :",
                                    view=view,
                                    ephemeral=True)


def is_admin_or_modo():

    async def predicate(ctx):
        admin_role = ctx.guild.get_role(ROLE_ADMIN_ID)
        modo_role = ctx.guild.get_role(ROLE_MODO_ID)
        return admin_role in ctx.author.roles or modo_role in ctx.author.roles

    return commands.check(predicate)


@bot.command(name="creer_tournoi")
@is_admin_or_modo()
async def creer_tournoi(ctx):

    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel

    try:
        await ctx.send("Création du tournoi - Indique le nom :")
        nom = (await bot.wait_for('message', check=check, timeout=120)).content
        if nom in tournois:
            await ctx.send("Un tournoi avec ce nom existe déjà.")
            return

        await ctx.send("Description :")
        description = (await bot.wait_for('message', check=check,
                                          timeout=120)).content

        await ctx.send("Date et heure (YYYY-MM-DD HH:MM) :")
        date_heure = (await bot.wait_for('message', check=check,
                                         timeout=120)).content

        await ctx.send("Jeu (Rocket League ou Fortnite) :")
        jeu = (await bot.wait_for('message', check=check, timeout=120)).content
        if jeu.lower() not in ["rocket league", "fortnite"]:
            await ctx.send("Jeu invalide.")
            return
        jeu = "Rocket League" if jeu.lower() == "rocket league" else "Fortnite"

        await ctx.send("Rangs acceptés (séparés par virgules) :")
        rangs_str = (await bot.wait_for('message', check=check,
                                        timeout=120)).content
        rangs_acceptes = [r.strip() for r in rangs_str.split(",")]

        await ctx.send("Nombre max de joueurs :")
        max_joueurs = int((await bot.wait_for('message',
                                              check=check,
                                              timeout=120)).content)

        await ctx.send("Cashprize (€) :")
        cashprize = (await bot.wait_for('message', check=check,
                                        timeout=120)).content
    except asyncio.TimeoutError:
        await ctx.send("⏱️ Temps écoulé. Annulation.")
        return
    except Exception:
        await ctx.send("Erreur lors de la saisie.")
        return

    tournois[nom] = {
        "description": description,
        "date_heure": date_heure,
        "jeu": jeu,
        "rangs_acceptes": rangs_acceptes,
        "max_joueurs": max_joueurs,
        "cashprize": cashprize,
        "message_id": None,
        "channel_id": None
    }
    inscriptions[nom] = {}

    embed = discord.Embed(title=f"Tournoi : {nom}", description=description)
    embed.add_field(name="Date / Heure", value=date_heure)
    embed.add_field(name="Jeu", value=jeu)
    embed.add_field(name="Rangs acceptés", value=", ".join(rangs_acceptes))
    embed.add_field(name="Max joueurs", value=str(max_joueurs))
    embed.add_field(name="Cashprize", value=str(cashprize) + " €")

    class InscriptionButton(Button):

        def __init__(self):
            super().__init__(label="S'inscrire",
                             style=discord.ButtonStyle.success,
                             custom_id=f"inscrire_{nom}")

        async def callback(self, interaction: discord.Interaction):
            user_id = interaction.user.id
            if user_id in inscriptions[nom]:
                await interaction.response.send_message("Déjà inscrit.",
                                                        ephemeral=True)
                return

            mod_channel = bot.get_channel(CHANNEL_TOURNOI_MODERATION_ID)
            view = View(timeout=None)

            class ValideButton(Button):

                def __init__(self):
                    super().__init__(label="Valider",
                                     style=discord.ButtonStyle.green)

                async def callback(self, btn_inter):
                    inscriptions[nom][user_id] = "Accepté"
                    await btn_inter.response.edit_message(
                        content=f"✅ <@{user_id}> accepté", view=None)
                    await interaction.user.send(
                        f"Inscription **{nom}** acceptée !")

            class RefuseButton(Button):

                def __init__(self):
                    super().__init__(label="Refuser",
                                     style=discord.ButtonStyle.red)

                async def callback(self, btn_inter):
                    inscriptions[nom][user_id] = "Refusé"
                    await btn_inter.response.edit_message(
                        content=f"❌ <@{user_id}> refusé", view=None)
                    await interaction.user.send(
                        f"Inscription **{nom}** refusée.")

            view.add_item(ValideButton())
            view.add_item(RefuseButton())

            inscriptions[nom][user_id] = "En attente"
            await mod_channel.send(
                f"Nouvelle inscription **{nom}** : <@{user_id}>", view=view)
            await interaction.response.send_message(
                "Demande envoyée à la modération.", ephemeral=True)

    view = View(timeout=None)
    view.add_item(InscriptionButton())

    channel = bot.get_channel(
        CHANNEL_TOURNOIS_RL_ANNONCE_ID if jeu ==
        "Rocket League" else CHANNEL_TOURNOIS_FN_ANNONCE_ID)
    message = await channel.send(embed=embed, view=view)
    tournois[nom]["message_id"] = message.id
    tournois[nom]["channel_id"] = channel.id

    await ctx.send(f"Tournoi **{nom}** créé dans {channel.mention} !")


@bot.command(name="supprimer_tournoi")
@is_admin_or_modo()
async def supprimer_tournoi(ctx, *, nom_tournoi):
    if nom_tournoi not in tournois:
        await ctx.send(f"Aucun tournoi nommé **{nom_tournoi}** n'a été trouvé."
                       )
        return

    del tournois[nom_tournoi]
    inscriptions.pop(nom_tournoi, None)

    await ctx.send(f"✅ Le tournoi **{nom_tournoi}** a bien été supprimé.")


@bot.command(name="liste_inscrits")
@is_admin_or_modo()
async def liste_inscrits(ctx, *, nom_tournoi):
    if nom_tournoi not in inscriptions:
        await ctx.send(
            f"Aucune inscription trouvée pour le tournoi **{nom_tournoi}**.")
        return

    joueurs = inscriptions[nom_tournoi]
    if not joueurs:
        await ctx.send(
            f"❌ Aucun joueur encore inscrit au tournoi **{nom_tournoi}**.")
        return

    msg = f"📋 Joueurs inscrits pour **{nom_tournoi}** :\n"
    for uid, statut in joueurs.items():
        membre = ctx.guild.get_member(uid)
        nom = membre.display_name if membre else f"<@{uid}>"
        msg += f"- {nom} : {statut}\n"

    await ctx.send(msg)


@bot.event
async def on_voice_state_update(member, before, after):
    guild = member.guild
    cat_rl = guild.get_channel(CATEGORY_RL_VOICE_ID)
    cat_fn = guild.get_channel(CATEGORY_FN_VOICE_ID)

    CREER_VOCAL_RL_ID = 1374068186361626695
    CREER_VOCAL_FN_ID = 1374068192997019648

    if after.channel and after.channel.id == CREER_VOCAL_RL_ID:
        new_vocal = await guild.create_voice_channel(
            f"salon-{member.display_name}", category=cat_rl)
        await member.move_to(new_vocal)

    elif after.channel and after.channel.id == CREER_VOCAL_FN_ID:
        new_vocal = await guild.create_voice_channel(
            f"salon-{member.display_name}", category=cat_fn)
        await member.move_to(new_vocal)

    if before.channel:
        if (before.channel.category_id in [
                CATEGORY_RL_VOICE_ID, CATEGORY_FN_VOICE_ID
        ] and before.channel.id not in [CREER_VOCAL_RL_ID, CREER_VOCAL_FN_ID]
                and len(before.channel.members) == 0):
            try:
                await before.channel.delete()
            except Exception as e:
                print(f"Erreur suppression vocal : {e}")


@bot.event
async def on_ready():
    print(f"Connecté en tant que {bot.user}")
    guild = bot.get_guild(GUILD_ID)
    channel = guild.get_channel(CHANNEL_CHOIX_JEU_ID)
    view = JeuSelectView()
    await channel.send("Choisis ton jeu :", view=view)


TOKEN = "MTM3MzY4MDQ2MDYwNTE2NTgwMQ.GtTNlb.Y6A8yrkRBjTS60StnGyeSExPPVKdABuFxbSYmE"
async def main():


    # Lancer le bot Discord (avec bot.start, pas bot.run)
    await bot.start(TOKEN)

if __name__ == "__main__":
    keep_alive()  # Lance le serveur Flask pour garder le bot en ligne
    asyncio.run(main())  # Démarre le bot Discord


