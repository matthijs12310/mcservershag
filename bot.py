import discord
import subprocess
import time
import signal
import requests
import re
import asyncio
import paramiko
from discord.ext import commands
from dotenv import load_dotenv

print(f"🔥 Loaded script as: {__name__}")

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
COMMAND = ["modal", "run", "-d", "main2.py"]
modal_lock = asyncio.Lock()

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

def get_ngrok_tcp_address():
    NGROK_API_TOKEN = "2vmwH73VHZ13kqvC8S7rW7881aw_712MU92jZYBhoq48SZnZG"
    url = "https://api.ngrok.com/endpoints"
    headers = {
        "Authorization": f"Bearer {NGROK_API_TOKEN}",
        "Ngrok-Version": "2"
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()

        for endpoint in data.get("endpoints", []):
            public_url = endpoint.get("public_url", "")
            if public_url.startswith("tcp://"):
                return public_url.replace("tcp://", "")

    except Exception as e:
        print(f"Error fetching ngrok address: {e}")
        return None

@bot.event
async def on_ready():
    print(f"✅ Bot is ready: {bot.user} (ID: {bot.user.id})")

@bot.command()
async def startmodal(ctx):
    print("🛠️ !startmodal command triggered.")
    if modal_lock.locked():
        await ctx.send("⚠️ A Modal start is already in progress.")
        return

    async with modal_lock:
        await ctx.send("⏳ Lock acquired. Starting modal...")

        try:
            # Step 1: Check for existing running Modal app
            check_process = subprocess.run(
                ["modal", "app", "list"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            existing_app_id = None
            for line in check_process.stdout.splitlines():
                if "ephemeral" in line and "ap-" in line:
                    match = re.search(r"(ap-[a-zA-Z0-9]+)", line)
                    if match:
                        existing_app_id = match.group(1)
                        break

            if existing_app_id:
                await ctx.send(f"⚠️ A Modal app is already running: `{existing_app_id}`")
                await ctx.send("If this is unexpected, you can stop it with `modal app stop`.")
                return

            await ctx.send("🚀 No active app found. Starting `modal run main2.py`...")

            process = subprocess.Popen(
                COMMAND,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                preexec_fn=lambda: signal.signal(signal.SIGINT, signal.SIG_IGN)
            )

            app_id = None
            ssh_line = None

            while True:
                line = process.stdout.readline()
                if not line:
                    break

                print(">>", line.strip())

                if "ssh into container using:" in line:
                    ssh_line = line.strip().replace("ssh into container using:", "").strip()

                if "modal.com/apps/" in line and "/main/" in line and app_id is None:
                    match = re.search(r"/main/(ap-[a-zA-Z0-9]+)", line)
                    if match:
                        app_id = match.group(1)

                if app_id and ssh_line:
                    print("✅ Got SSH and App ID, starting setup_minecraft_server")
                    await ctx.send(f"🔑 SSH Info:\n```\n{ssh_line}\n```")
                    await ctx.send(f"🆔 App ID: `{app_id}`")

                    bot.loop.create_task(monitor_logs(app_id, ctx))
                    await setup_minecraft_server(ssh_line, ctx)
                    break

            process.send_signal(signal.SIGINT)
            try:
                process.wait(timeout=10)
                print("Process completed.")
            except subprocess.TimeoutExpired:
                process.kill()

        except Exception as e:
            await ctx.send(f"❌ Unexpected error: {e}")

async def monitor_logs(app_id, ctx):
    def watch_logs_blocking():
        log_command = ["modal", "app", "logs", app_id]
        log_process = subprocess.Popen(
            log_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        print(f"📡 Monitoring logs for App ID: {app_id}")
        while True:
            line = log_process.stdout.readline()
            if not line:
                break
            print("LOG>>", line.strip())

    await asyncio.to_thread(watch_logs_blocking)
    await ctx.send("🛑 Modal service has stopped.")

async def setup_minecraft_server(ssh_line, ctx):
    print("🚧 Running setup_minecraft_server...")
    match = re.search(r"ssh -p (\d+) root@([\w\.\-]+)", ssh_line)
    if not match:
        await ctx.send("❌ Could not parse SSH connection info.")
        return

    port = int(match.group(1))
    host = match.group(2)
    username = "root"
    ssh_key_path = "/root/.ssh/id_rsa"

    await ctx.send(f"🔗 Connecting to `{host}:{port}` via SSH...")

    try:
        key = paramiko.RSAKey.from_private_key_file(ssh_key_path)
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname=host, port=port, username=username, pkey=key)

        sftp = ssh.open_sftp()
        sftp.put("setup_minecraft.sh", "/root/setup_minecraft.sh")
        sftp.close()

        await ctx.send("📤 Uploaded setup script. Running it now...")

        commands = [
            "chmod +x /root/setup_minecraft.sh",
            "bash /root/setup_minecraft.sh"
        ]

        for cmd in commands:
            stdin, stdout, stderr = ssh.exec_command(cmd)
            for line in stdout:
                print("REMOTE OUT:", line.strip())
            for line in stderr:
                print("REMOTE ERR:", line.strip())

        ssh.close()
        time.sleep(3)
        ngrok_ip = get_ngrok_tcp_address()
        if ngrok_ip:
            await ctx.send(f"🌐 Ngrok TCP address:\n```\n{ngrok_ip}\n```")
        else:
            await ctx.send("❌ Could not retrieve Ngrok TCP address from API.")
        await ctx.send("✅ Minecraft server launched in tmux session `mcserver`.")

    except Exception as e:
        await ctx.send(f"❌ SSH error: {str(e)}")
        print("SSH ERROR:", e)

if __name__ == "__main__":
    print("🚀 Calling bot.run()")
    bot.run(TOKEN)
