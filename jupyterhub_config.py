import os
c = get_config()

# ==========================================
# 1. Spawner 設定 (告訴系統用 Docker 產生運算環境)
# ==========================================
c.JupyterHub.spawner_class = 'dockerspawner.DockerSpawner'

# 這是使用者登入後預設啟動的 Image。
# 實務上請換成有裝 CUDA + PyTorch/TensorFlow 的 Image，
# 例如: 'cschranz/gpu-jupyter:v1.6_cuda-11.6_ubuntu-20.04' 
c.DockerSpawner.image = 'jupyter/scipy-notebook:latest'

# ==========================================
# 2. GPU 與效能設定 (發揮 96GB 怪獸效能的關鍵)
# ==========================================
c.DockerSpawner.extra_host_config = {
    "device_requests": [
        {
            "Driver": "nvidia",
            "Count": -1,  # -1 代表授權存取所有 GPU
            "Capabilities": [["gpu", "compute", "utility"]]
        }
    ],
    # 加大共用記憶體，避免 PyTorch DataLoader 訓練時崩潰
    "shm_size": "16G" 
}

# ==========================================
# 3. 網路與系統設定
# ==========================================
# 讓 Hub 與生成的 Container 可以互相溝通
network_name = os.environ['DOCKER_NETWORK_NAME']
c.DockerSpawner.network_name = network_name
c.JupyterHub.hub_ip = 'jupyterhub'

# ==========================================
# 4. 儲存空間設定 (讓使用者的資料重啟後不遺失)
# ==========================================
notebook_dir = '/home/jovyan/work'
c.DockerSpawner.notebook_dir = notebook_dir
# 將 Docker volume 綁定到容器內
c.DockerSpawner.volumes = { 
    # 保險箱 A：保護程式碼與資料 (沿用你原本的名字，資料才不會不見)
    'jupyterhub-user-{username}': notebook_dir,
    # 保險箱 B：專門保護 Conda 虛擬環境與快取
    'jupyterhub-conda-{username}': '/home/jovyan/.conda',
     }



# ==========================================
# 注入環境變數 (自動修改 Conda 的預設路徑到保險箱內)
# ==========================================
c.DockerSpawner.environment = {
    # 設定虛擬環境的預設儲存位置
    'CONDA_ENVS_DIRS': '/home/jovyan/.conda/envs',
    # 設定下載套件的快取位置 (這樣重裝套件會很快，且不會因為重啟而消失)
    'CONDA_PKGS_DIRS': '/home/jovyan/.conda/pkgs',
    # 2. [神來一筆] 將 Jupyter Kernel (門牌) 預設儲存位置導流
    # 以後 ipykernel install --user 都會自動存到這個被保護的資料夾
    'JUPYTER_DATA_DIR': '/home/jovyan/.conda/jupyter_data',
    
    # 3. [加碼保護] 將 pip install --user 裝的套件也導流進來
    'PYTHONUSERBASE': '/home/jovyan/.conda/local_python'
}

# ==========================================
# 5. 帳號認證設定 (使用 Native Authenticator)
# ==========================================
c.JupyterHub.authenticator_class = 'nativeauthenticator.NativeAuthenticator'
c.Authenticator.allow_all = True
# 開放讓使用者在登入頁面自己點擊 "Signup" 註冊
c.NativeAuthenticator.open_signup = True
# 設定一組管理員帳號 (註冊後免審核，並可在後台審核其他人)
c.Authenticator.admin_users = {'admin'}
# 一般使用者註冊後，需要管理員在後台點擊審核通過才能登入
c.NativeAuthenticator.check_common_password = True
c.NativeAuthenticator.minimum_password_length = 8

