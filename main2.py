import subprocess
import time

import modal

app = modal.App(name="kanker")
image = (
    modal.Image.debian_slim()
    .apt_install("openssh-server")
    .run_commands("mkdir /run/sshd")
    .add_local_file("/root/.ssh/id_rsa.pub", "/root/.ssh/authorized_keys", copy=True)
)


@app.function(image=image, region="eu-west", timeout=86400)
def some_function():
    subprocess.Popen(["/usr/sbin/sshd", "-D", "-e"])
    with modal.forward(port=22, unencrypted=True) as tunnel:
        hostname, port = tunnel.tcp_socket
        connection_cmd = f'ssh -p {port} root@{hostname}'
        print(f"ssh into container using: {connection_cmd}")
        while True: time.sleep(1)  # keep alive for 1 hour or until killed
