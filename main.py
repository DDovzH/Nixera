import discord
from discord.ext import commands
from pytube import YouTube
from pytube import Search
import asyncio
import os
from collections import deque

intents = discord.Intents.all()

bot = commands.Bot(command_prefix='/', intents=intents)

voice_connections = {}
queues = {}
# playlist = {}
MAX_QUEUE_LENGTH = 10


def download_audio(url):
    try:
        if "https" in url:
            yt = YouTube(url)
            audio_stream = yt.streams.filter(only_audio=True).first()
        else:
            audio_stream = Search(url).results[0].streams.filter(only_audio=True).get_audio_only()

        if os.path.isfile(audio_stream.default_filename):
            return audio_stream.default_filename
        else:
            audio_stream.download()
            return audio_stream.default_filename

    except Exception as e:
        print(f"Error downloading audio: {e}")
        return None


def play_next(ctx):
    if ctx.guild.id in queues:
        if queues[ctx.guild.id]:
            audio_filename = queues[ctx.guild.id].popleft()
            vc = voice_connections[ctx.guild.id]
            vc.play(discord.FFmpegPCMAudio(
                executable="ffmpeg-2023-09-07-git-9c9f48e7f2-essentials_build/bin/ffmpeg.exe",
                source=audio_filename), after=lambda e: play_next(ctx))


@bot.command()
async def skip(ctx):
    if ctx.author.voice is None:
        await ctx.send("You must be in a voice channel to use this command.")
        return

    if ctx.guild.id in voice_connections:
        vc = voice_connections[ctx.guild.id]

        if vc.is_playing():
            vc.stop()
            await ctx.send("The current track has been skipped.")
        else:
            await ctx.send("There is no active track to skip.")
    else:
        await ctx.send("The bot is not in a voice channel.")


@bot.command()
async def play(ctx, *args):
    try:
        if ctx.author.voice is None:
            await ctx.send("You must be in a voice channel to use this command.")
            return

        channel = ctx.author.voice.channel

        if channel.guild.id in voice_connections:
            vc = voice_connections[channel.guild.id]
        else:
            vc = await channel.connect()
            voice_connections[channel.guild.id] = vc

        if args:
            url = ' '.join(args)
            audio_filename = download_audio(url)
            if audio_filename:
                if ctx.guild.id not in queues:
                    queues[ctx.guild.id] = deque(maxlen=MAX_QUEUE_LENGTH)

                queues[ctx.guild.id].append(audio_filename)
                if not vc.is_playing():
                    play_next(ctx)
            else:
                await ctx.send("Failed to download the track.")

    except Exception as e:
        await ctx.send(f"Error: {e}")


@bot.command()
async def stop(ctx):
    if ctx.author.voice is None:
        await ctx.send("You must be in a voice channel to use this command.")
        return

    if ctx.guild.id in voice_connections:
        vc = ctx.voice_client
        vc.stop()
        await vc.disconnect()

        if ctx.guild.id in voice_connections:
            del voice_connections[ctx.guild.id]
            del queues[ctx.guild.id]
            # del playlist[ctx.guild.id]

        await asyncio.sleep(5)

        root_directory = os.getcwd()
        for filename in os.listdir(root_directory):
            if filename.endswith(".mp4"):
                try:
                    os.remove(filename)
                except Exception as e:
                    print(e)
    else:
        await ctx.send("The bot is not in a voice channel.")


bot.run(f'{os.environ.get("DISCORD_KEY")}')
