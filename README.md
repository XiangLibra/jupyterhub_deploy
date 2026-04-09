

***


# JupyterHub + DockerSpawner 多人 GPU 算力平台建置指南

本指南旨在於單一 Linux 伺服器上，建立一個允許多個帳號透過網址登入，並各自擁有獨立 Docker 運算環境的 JupyterHub 平台。
特別針對擁有大容量 VRAM（如 NVIDIA RTX PRO 6000 96GB）的單張 GPU，採用 **Time-Slicing（時間切片）** 技術讓多使用者共享算力。

## 系統環境與硬體要求
* **作業系統**：Ubuntu 22.04 / 24.04 (推薦)
* **GPU**：NVIDIA GPU (本專案以單張 96GB 顯卡為例)
* **基礎軟體**：已安裝 Docker、Docker Compose、NVIDIA Driver。

---

## Step 1: 安裝與驗證 NVIDIA Container Toolkit
必須安裝此套件，Docker 容器才能讀取到本機的 GPU。

1. 依照 [NVIDIA 官方文件](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html) 安裝 `nvidia-container-toolkit`。
2. 驗證安裝是否成功（若成功會顯示本機 GPU 資訊）：
   ```bash
   sudo docker run --rm --gpus all ubuntu nvidia-smi
   ```

---

## Step 2: 準備專案與設定檔

### 安裝docker
``` bash
# 安裝 Docker 引擎與 Docker Compose
sudo apt install -y docker.io docker-compose

# 啟動 Docker 服務，並設定為開機自動啟動
sudo systemctl start docker
sudo systemctl enable docker

# (選擇性) 將目前的使用者加入 docker 群組，以後打 docker 指令就不用加 sudo
sudo usermod -aG docker $USER
# 注意：執行完上行指令後，需登出再重新登入 SSH 才會生效。
```

建立一個專案資料夾（例如 `jupyterhub-deploy`），並在裡面建立以下三個關鍵檔案：

### 1. `Dockerfile` (客製化 Hub 映像檔)
官方預設環境不包含我們需要的認證與生成套件，因此需要自行打包。

```dockerfile
# 使用官方 JupyterHub 作為基底
FROM jupyterhub/jupyterhub:latest

# 安裝 DockerSpawner 與 NativeAuthenticator
RUN pip install --no-cache-dir \
    dockerspawner \
    jupyterhub-nativeauthenticator
```

### 2. `jupyterhub_config.py` (核心設定檔)
此設定檔涵蓋了 Docker 容器生成、96GB GPU 共享設定，以及 NativeAuthenticator 註冊認證機制。

```python
import os
c = get_config()

# ==========================================
# 1. Spawner 設定 (使用 Docker 生成運算環境)
# ==========================================
c.JupyterHub.spawner_class = 'dockerspawner.DockerSpawner'

# 預設啟動的 Image，可換成包含 PyTorch/TensorFlow 的 GPU Image
c.DockerSpawner.image = 'jupyter/scipy-notebook:latest'

# ==========================================
# 2. GPU 與效能設定 (共享大容量 GPU 的關鍵)
# ==========================================
c.DockerSpawner.extra_host_config = {
    "device_requests": [
        {
            "Driver": "nvidia",
            "Count": -1,  # 授權存取所有 GPU (Time-slicing 共用)
            "Capabilities": [["gpu", "compute", "utility"]]
        }
    ],
    # 加大共用記憶體，避免深度學習 DataLoader 訓練時崩潰
    "shm_size": "16G" 
}

# ==========================================
# 3. 網路與系統設定
# ==========================================
network_name = os.environ['DOCKER_NETWORK_NAME']
c.DockerSpawner.network_name = network_name
c.JupyterHub.hub_ip = 'jupyterhub'

# ==========================================
# 4. 儲存空間設定 (讓使用者的資料重啟後不遺失)
# ==========================================
notebook_dir = '/home/jovyan/work'
c.DockerSpawner.notebook_dir = notebook_dir
# 將 Docker volume 綁定到容器內
c.DockerSpawner.volumes = { 'jupyterhub-user-{username}': notebook_dir }

# ==========================================
# 5. 帳號認證設定 (使用 Native Authenticator)
# ==========================================
c.JupyterHub.authenticator_class = 'nativeauthenticator.NativeAuthenticator'

# [重要] 解決 JupyterHub 5.x 預設阻擋所有登入的問題
c.Authenticator.allow_all = True 

# 開放註冊功能
c.NativeAuthenticator.open_signup = True
# 設定最高管理員帳號 (註冊後免審核)
c.Authenticator.admin_users = {'admin'}

# 密碼安全限制
c.NativeAuthenticator.check_common_password = True
c.NativeAuthenticator.minimum_password_length = 8
```

### 3. `docker-compose.yml` (啟動腳本)
負責啟動 JupyterHub 服務，並給予其控制底層 Docker 的權限。

```yaml
version: '3.8'

services:
  jupyterhub:
    build: .
    container_name: jupyterhub
    # [重要] 強制指定設定檔路徑，避免吃到預設 PAM 認證
    command: jupyterhub -f /srv/jupyterhub/jupyterhub_config.py 
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - ./jupyterhub_data:/srv/jupyterhub
      - ./jupyterhub_config.py:/srv/jupyterhub/jupyterhub_config.py
    environment:
      DOCKER_NETWORK_NAME: jupyterhub-network
    ports:
      # 左邊的主機 Port 若遇衝突 (如 8000 已被佔用)，可修改為 8080 或 8888
      - "8000:8000"
    networks:
      - jupyterhub-network
    restart: always

networks:
  jupyterhub-network:
    name: jupyterhub-network
```

---

## Step 3: 啟動服務

在該專案資料夾下，執行以下指令啟動：

```bash
sudo docker-compose up -d
```

檢查服務是否健康運行 (`State` 應顯示為 `Up`)：
```bash
sudo docker-compose ps
```

看執行日誌
```bash
sudo docker-compose logs -f
```
---

## Step 4: 帳號註冊與後台授權流程

### 1. 建立最高管理員 (`admin`)
1. 開啟瀏覽器，進入網址：`http://<伺服器IP>:8000/hub/signup`
2. **Username** 必須精準輸入 `admin`。
3. 設定密碼並送出，看到 `The signup was successful!` 即代表成功。
4. 返回登入頁面 (`/hub/login`)，使用 `admin` 登入。

### 2. 一般使用者註冊與核准
1. 一般團隊成員（如 `user1`, `admin1`）同樣至 `/hub/signup` 註冊。
2. 註冊後，一般帳號會處於「**待審核**」狀態，無法直接登入。
3. **由 `admin` 開通**：
   * 使用 `admin` 帳號登入系統。
   * 點擊右上角 **Admin** 進入控制台。
   * 點擊 **Authorize** 分頁。
   * 找到待審核的使用者，點擊旁邊的 **Authorize** 按鈕即可開通權限。

---

## Step 5: 驗證 GPU 運算環境
使用者登入並點擊 **Start My Server** 後（首次啟動需等待下載 Image），系統會開啟 JupyterLab 介面。

1. 點擊 **Terminal** 開啟終端機。
2. 輸入以下指令驗證硬體：
   ```bash
   nvidia-smi
   ```
3. 若能成功看見 96GB 的 GPU 資訊，代表個人獨立的 GPU 算力容器已完美建置完成！





# jupyter中下載不同python環境和切換方法


以下是具體的操作步驟，請在 Jupyter 的 Terminal 裡面跟著做：

### 🛠️ 把 Conda 環境加入 Jupyter Kernel 選單的步驟

假設你剛剛建立的 conda 環境叫做 `py310`，請依序執行：
建立conda 的python3.10的環境(可以自行選擇其他版本或者虛擬環境名稱)
```bash
conda create --name py310 python=3.10  -y
```

**1. 啟動並進入你的 conda 環境**
```bash
conda activate py310
```
*(你的命令列提示字元前面應該會多出 `(py310)` 的字樣)*

**2. 在該環境中安裝溝通橋樑 (`ipykernel`)**
這個套件是 Jupyter 用來控制 Python 環境的必備工具。
```bash
pip install ipykernel
```

**3. 將環境註冊到 Jupyter 的目錄中（掛上門牌）**
執行以下指令，把這個環境正式介紹給 Jupyter 認識：
```bash
python -m ipykernel install --user --name myenv --display-name "Python (py310)"
```
* `--name py310`：系統底層辨識用的名稱（通常跟你的 conda 環境同名）。
* `--display-name "Python (py310)"`：**這是你希望在 Jupyter 選單上看到的漂亮名稱**，你可以隨便改，例如改成 `"PyTorch 2.0 (Python 3.10)"`。

**4. 重新整理網頁**
完成上述指令後，直接**按 F5 重新整理**你的 JupyterLab 網頁。
接著點擊右上角的 Kernel 選擇器，或者在 Launcher 首頁，你就會看到剛剛新增的 `"Python (py310)"` 選項出現了！

---

### 💡 補充：如果以後想刪除這個 Kernel 怎麼辦？

如果你之後把 conda 環境刪掉了，但 Jupyter 選單裡還是卡著那個舊名字（變成殭屍選項），你可以用以下指令把它清掉：

1. 先查看目前 Jupyter 記住了哪些 Kernel：
   ```bash
   jupyter kernelspec list
   ```
2. 刪除你不要的 Kernel（假設底層名稱是 `py310`）：
   ```bash
   jupyter kernelspec uninstall myenv
   ```
   系統會問你 `[y/N]`，輸入 `y` 即可刪除。





# admin 來管理觀看容器執行狀況




1. **JupyterHub 主控台容器**：負責管理登入、註冊、分配資源的「大腦」（名字通常叫 `jupyterhub`）。
2. **使用者專屬運算容器**：你登入後點擊 "Start My Server" 所產生，真正掛載 96GB GPU 且用來寫程式的「個人房間」（名字通常叫 `jupyter-你的帳號名`，例如 `jupyter-admin`）。

以下是進入容器的具體方法：

### 方法一：從伺服器終端機進入 (標準 Docker 做法)

這是最高權限的做法，適用於你想進入任何容器修改底層設定時。

**第 1 步：找出容器的正確名稱**
在你的伺服器終端機輸入以下指令，列出目前所有正在運作的容器：
```bash
sudo docker ps
```
你會在最右邊的 `NAMES` 欄位看到容器的名字，例如 `jupyterhub` 或 `jupyter-admin`。

**第 2 步：執行 `docker exec` 指令進入容器**
假設你想進入 `admin` 這個使用者的運算容器，請輸入：
```bash
sudo docker exec -it jupyter-admin /bin/bash
```
* *(如果是想進入主控台，就把名字換成 `jupyterhub`)*
* `exec`：代表要在運作中的容器內執行指令。
* `-it`：代表開啟一個互動式的終端機介面。
* `/bin/bash`：代表你要啟動 Bash 殼層（這就是 Linux 終端機的程式）。

**✅ 成功畫面**：
你的命令列開頭會突然改變，變成類似 `jovyan@a1b2c3d4e5f6:~$`，這代表你已經「穿越」進到容器內部了！
*(註：`jovyan` 是官方 Jupyter Image 預設的使用者名稱)*

**🚪 如何離開容器？**
只要輸入 `exit` 並按下 Enter，就會退回到你原本伺服器的終端機了。

---

### 方法二：直接從網頁版 JupyterLab 進入 (最簡單、最常用)

如果你只是想要安裝 Python 套件（例如 `pip install`、`conda install`）、操作 Git，或是執行 `nvidia-smi` 來監控你那張 96GB 的 GPU，**其實你根本不需要從伺服器底層下 docker 指令！**

1. 用你的帳號（例如 `admin`）從瀏覽器登入 JupyterHub。
2. 進入 JupyterLab 介面後，在 **Launcher（啟動頁面）** 點擊 **Terminal（終端機）** 圖示。
3. 彈出的黑色視窗，**就已經是這個容器的內部了！**

你在這個網頁版 Terminal 裡做的所有操作（包含剛剛教你的設定 Conda 與 Jupyter Kernel），完全等同於你用 `docker exec` 進來做的操作，而且權限剛好對應你這個使用者，是最安全也最方便的做法。
