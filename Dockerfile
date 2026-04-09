# 使用官方 JupyterHub 作為基底
FROM jupyterhub/jupyterhub:latest

# 安裝 DockerSpawner 與 NativeAuthenticator (內建的註冊/登入系統)
RUN pip install --no-cache-dir \
    dockerspawner \
    jupyterhub-nativeauthenticator