# GCP + Docker + FastAPI 설치 가이드

> 인스턴스 생성 → 고정 IP 설정 → SSH 키 설정 → 서버 초기화 → Docker 설치 → FastAPI 컨테이너 실행까지  
> 기술적 원리와 함께 설명하는 상세 가이드

---

## 목차

1. [GCP 인스턴스 생성](#1-gcp-인스턴스-생성)
2. [고정 IP(정적 외부 IP) 설정](#2-고정-ip정적-외부-ip-설정)
3. [SSH 키 생성 및 로컬 접속 설정](#3-ssh-키-생성-및-로컬-접속-설정)
4. [서버 초기 설정](#4-서버-초기-설정)
5. [Docker 설치](#5-docker-설치)
6. [FastAPI 컨테이너 실행](#6-fastapi-컨테이너-실행)

---

## 1. GCP 인스턴스 생성

### 1-1. 프로젝트 준비

[Google Cloud Console](https://console.cloud.google.com)에 접속한 뒤, 상단 프로젝트 선택 드롭다운에서 **새 프로젝트**를 만듭니다.

> 💡 **왜 프로젝트를 만드나요?**  
> GCP의 모든 리소스(서버, API, 네트워크 등)는 프로젝트 단위로 관리됩니다. 프로젝트를 분리해두면 나중에 삭제하거나 비용을 추적할 때 훨씬 편리합니다.

### 1-2. VM 인스턴스 생성

좌측 메뉴에서 `Compute Engine` → `VM 인스턴스` → **만들기** 클릭.

아래 설정을 그대로 따라 입력하세요.

**① 기본 정보**

| 항목 | 값 |
|---|---|
| 이름 | `fastapi-server` (원하는 이름 가능) |
| 리전 | `us-east1` |
| 영역 | `us-east1-b` |

> 💡 **리전이 왜 미국이어야 하나요?**  
> GCP 무료 티어(Always Free)는 `us-east1`, `us-west1`, `us-central1` 세 리전에서만 e2-micro 인스턴스를 무료로 제공합니다. 서울 리전(`asia-northeast3`)을 선택하면 **요금이 발생**합니다.

**② 머신 구성**

| 항목 | 값 |
|---|---|
| 시리즈 | E2 |
| 머신 유형 | `e2-micro` |

> 💡 **e2-micro 스펙은?**  
> CPU 0.25 vCPU (버스트 가능), RAM 1GB입니다. FastAPI는 idle 상태에서 메모리를 50MB 이하로 유지할 수 있어서 e2-micro에서도 여유 있게 동작합니다.

**③ 부팅 디스크**

`변경` 버튼 클릭 후:

| 항목 | 값 |
|---|---|
| 운영체제 | Ubuntu |
| 버전 | Ubuntu 24.04 LTS |
| 부팅 디스크 유형 | **표준 영구 디스크 (HDD)** |
| 크기 | 30GB |

> 💡 **왜 SSD가 아니라 HDD인가요?**  
> SSD(균형 있는 영구 디스크)는 유료입니다. 표준 HDD 30GB는 무료 티어에 포함됩니다. 자동화 스크립트 실행 정도의 워크로드에는 HDD로 충분합니다.

**④ 방화벽**

- `HTTP 트래픽 허용` ✅ 체크
- `HTTPS 트래픽 허용` ✅ 체크

**⑤ 만들기** 클릭

### 1-3. FastAPI 포트 방화벽 규칙 추가

FastAPI(uvicorn)는 기본적으로 **8000번 포트**를 사용합니다. GCP는 기본적으로 이 포트를 막아두므로, 방화벽 규칙을 별도로 열어줘야 합니다.

`VPC 네트워크` → `방화벽` → **방화벽 규칙 만들기**

| 항목 | 값 |
|---|---|
| 이름 | `allow-fastapi` |
| 트래픽 방향 | 수신 (Ingress) |
| 일치 시 작업 | 허용 |
| 대상 | 네트워크의 모든 인스턴스 |
| 소스 IPv4 범위 | `내 IP주소/32` (보안 권장) 또는 `0.0.0.0/0` (전체 허용) |
| 프로토콜 및 포트 | TCP → `8000` |

> 💡 **`/32`가 무엇인가요?**  
> IP 뒤의 `/32`는 서브넷 마스크로, "이 IP 주소 딱 하나만"을 의미합니다. 즉 내 컴퓨터의 IP에서만 접근 허용 → 보안상 훨씬 안전합니다. 내 IP는 [https://whatismyip.com](https://whatismyip.com)에서 확인 가능합니다.

---

## 2. 고정 IP(정적 외부 IP) 설정

### 2-1. 고정 IP가 왜 필요한가요?

GCP 인스턴스를 처음 만들면 **임시(Ephemeral) 외부 IP**가 자동으로 부여됩니다. 이 IP는 **인스턴스를 중지하고 다시 시작하면 바뀝니다.**

이렇게 되면 두 가지 문제가 생깁니다.

1. **SSH 접속 설정이 깨짐** — `~/.ssh/config`에 IP를 하드코딩했다면, 매번 바뀐 IP로 수정해야 합니다.
2. **서버 주소가 바뀜** — 북마크해둔 URL이나 연동해둔 설정이 무효화됩니다.

고정 IP(정적 외부 IP)를 설정하면 서버를 껐다 켜도 항상 같은 IP를 유지할 수 있습니다.

> ⚠️ **비용 주의**  
> GCP는 **VM에 연결되어 사용 중인** 정적 IP는 무료입니다. 단, 정적 IP를 예약해두고 VM에 연결하지 않은 채 방치하면 요금이 발생합니다. VM을 삭제할 때 정적 IP도 함께 해제하는 것을 잊지 마세요.

### 2-2. 정적 IP 예약

GCP Console → `VPC 네트워크` → `IP 주소` → **외부 정적 IP 주소 예약** 클릭.

| 항목 | 값 |
|---|---|
| 이름 | `fastapi-static-ip` (원하는 이름) |
| 네트워크 서비스 등급 | 표준 (Standard) |
| IP 버전 | IPv4 |
| 유형 | 지역(Regional) |
| 리전 | `us-east1` ← 인스턴스와 **반드시 같은 리전** |

**예약** 클릭 후 잠시 기다리면 IP 주소가 생성됩니다.

> 💡 **지역(Regional) vs 전역(Global)?**  
> 전역 IP는 HTTP(S) 로드 밸런서에서만 사용 가능합니다. 일반 VM에 붙이려면 반드시 **지역(Regional)**을 선택해야 합니다.

> 💡 **네트워크 서비스 등급 - 표준 vs 프리미엄?**  
> 프리미엄은 Google의 전용 글로벌 네트워크를 통해 트래픽이 라우팅됩니다. 속도가 빠르지만 비쌉니다. 표준은 일반 인터넷을 통해 라우팅됩니다. 개인 서버 용도로는 표준으로 충분합니다.

### 2-3. 예약한 IP를 VM에 연결

위 단계에서 만든 정적 IP 목록에서, 방금 예약한 IP 항목의 오른쪽 `•••` 메뉴 → **정적 주소 연결** 클릭.

| 항목 | 값 |
|---|---|
| 리소스 | `fastapi-server` (생성한 VM 이름 선택) |

**연결** 클릭.

VM의 외부 IP가 방금 예약한 정적 IP로 바뀐 것을 `VM 인스턴스` 목록에서 확인할 수 있습니다.

> 💡 **이미 실행 중인 VM에 연결해도 되나요?**  
> 네, VM을 중지하지 않아도 됩니다. IP만 교체되며 SSH 연결에는 영향을 주지 않습니다. 단, SSH 접속 시 사용하는 IP 주소는 새 IP로 업데이트해야 합니다.

### 2-4. 기존 임시 IP와의 차이 확인

`VM 인스턴스` 목록에서 외부 IP 옆에 아무 표시가 없으면 임시 IP, `정적` 표시가 있으면 정적 IP입니다.

이제 VM을 중지하고 재시작해도 이 IP는 변하지 않습니다. 앞으로 나오는 `<GCP_외부_IP>` 자리에 이 고정 IP를 사용하면 됩니다.

---

## 3. SSH 키 생성 및 로컬 접속 설정

### 3-1. SSH가 뭔가요?

SSH(Secure Shell)는 네트워크를 통해 원격 서버에 **암호화된 방식으로 접속**하는 프로토콜입니다.  
GCP 웹 콘솔의 브라우저 SSH 터미널을 써도 되지만, **로컬 터미널에서 직접 접속하는 게 훨씬 빠르고 편리**합니다.

SSH 접속에는 **공개 키 / 개인 키 쌍**을 사용합니다.
- **개인 키(Private Key)**: 내 컴퓨터에 보관. 절대 외부에 공유하면 안 됨.
- **공개 키(Public Key)**: 서버에 등록. 공개해도 괜찮음.

접속 시 서버는 "이 공개 키에 대응하는 개인 키를 가진 사람이냐?"를 확인합니다. 비밀번호 없이도 안전하게 인증할 수 있는 원리입니다.

### 3-2. 로컬에서 SSH 키 생성

**Mac / Linux** 터미널, 또는 **Windows**의 PowerShell / Git Bash를 열고:

```bash
# SSH 키 생성 (RSA 4096비트)
ssh-keygen -t rsa -b 4096 -C "your_email@example.com" -f ~/.ssh/gcp_fastapi
```

| 옵션 | 의미 |
|---|---|
| `-t rsa` | 암호화 알고리즘을 RSA로 지정 |
| `-b 4096` | 키 길이를 4096비트로 설정 (보안 강화) |
| `-C "..."` | 키에 붙는 코멘트 (이메일로 식별 용도) |
| `-f ~/.ssh/gcp_fastapi` | 생성할 파일 경로와 이름 지정 |

실행하면 비밀번호(passphrase)를 입력하라고 합니다. 빈칸으로 엔터를 눌러도 되지만, 보안을 위해 설정해두는 것을 권장합니다.

생성된 파일:
- `~/.ssh/gcp_fastapi` → **개인 키** (절대 공유 금지)
- `~/.ssh/gcp_fastapi.pub` → **공개 키** (서버에 등록할 파일)

### 3-3. 공개 키 내용 확인

```bash
cat ~/.ssh/gcp_fastapi.pub
```

아래와 같은 형태의 텍스트가 출력됩니다. 이 내용을 복사해 둡니다.

```
ssh-rsa AAAAB3NzaC1yc2EAAAA... (긴 문자열) ... your_email@example.com
```

### 3-4. GCP에 공개 키 등록

GCP Console → `Compute Engine` → `설정` → **메타데이터** → `SSH 키` 탭 → **추가**

복사해 둔 공개 키 전체 내용을 붙여넣고 저장합니다.

> 💡 **메타데이터에 등록하면?**  
> 해당 프로젝트의 모든 VM에 적용됩니다. 특정 VM에만 등록하고 싶다면 `VM 인스턴스` → 해당 VM 클릭 → `수정` → SSH 키 항목에 등록하세요.

### 3-5. 로컬에서 SSH 접속

GCP 콘솔의 VM 인스턴스 목록에서 **외부 IP**를 확인합니다. (예: `34.123.45.67`)

```bash
ssh -i ~/.ssh/gcp_fastapi <GCP_계정_사용자명>@<외부_IP>
```

> 💡 **사용자명이 뭔가요?**  
> GCP는 기본적으로 로컬 컴퓨터의 사용자 계정명을 서버 사용자명으로 사용합니다.  
> Mac에서 `whoami`를 치면 나오는 이름이 바로 그것입니다.  
> GCP 콘솔의 웹 SSH 창 상단에도 `username@fastapi-server` 형태로 표시됩니다.

접속 예시:
```bash
ssh -i ~/.ssh/gcp_fastapi johndoe@34.123.45.67
```

처음 접속 시 `Are you sure you want to continue connecting?` 메시지가 나오면 `yes` 입력.

### 3-6. SSH Config 설정 (편의 기능)

매번 긴 명령어를 입력하기 귀찮다면 `~/.ssh/config` 파일에 단축 설정을 추가할 수 있습니다.

```bash
nano ~/.ssh/config
```

아래 내용 추가:

```
Host gcp-fastapi
    HostName 34.123.45.67
    User johndoe
    IdentityFile ~/.ssh/gcp_fastapi
```

저장 후, 이제부터는 아래 명령어 하나로 접속 가능합니다.

```bash
ssh gcp-fastapi
```

> 💡 **`~/.ssh/config`는 뭔가요?**  
> SSH 클라이언트의 설정 파일입니다. 접속 대상에 별칭(alias)을 붙이고, 사용할 키 파일이나 포트 등을 미리 지정해 둘 수 있어 반복 접속 시 매우 편리합니다.

---

## 4. 서버 초기 설정

SSH로 인스턴스에 접속한 상태에서 아래 단계를 진행합니다.

### 4-1. 패키지 업데이트

```bash
sudo apt update && sudo apt upgrade -y
```

> 💡 **이게 왜 필요한가요?**  
> 클라우드 VM 이미지는 생성 시점의 패키지 버전으로 배포됩니다. 실제 사용 시점까지 보안 패치나 버그 수정이 누적되어 있을 수 있어서, 처음 접속하면 항상 업데이트를 먼저 합니다.  
> `apt update`는 패키지 목록을 최신화하고, `apt upgrade -y`는 실제 설치된 패키지들을 최신 버전으로 업그레이드합니다. (`-y`는 확인 없이 자동 진행)

### 4-2. Swap 메모리 설정

e2-micro의 RAM은 1GB입니다. Docker 빌드나 의존성 설치 과정에서 일시적으로 메모리가 치솟을 수 있으므로 **Swap**을 설정해 보완합니다.

```bash
# 2GB 크기의 swap 파일 생성
sudo fallocate -l 2G /swapfile

# 파일 권한을 root만 읽을 수 있도록 설정 (보안)
sudo chmod 600 /swapfile

# 해당 파일을 swap 영역으로 포맷
sudo mkswap /swapfile

# swap 활성화
sudo swapon /swapfile

# 재부팅 후에도 자동으로 swap을 사용하도록 /etc/fstab에 등록
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

# 메모리 상태 확인
free -h
```

`Swap` 항목에 `2.0G`가 표시되면 성공입니다.

> 💡 **Swap이 뭔가요?**  
> RAM이 꽉 찼을 때 디스크의 일부를 임시 메모리처럼 사용하는 기술입니다. 속도는 RAM보다 훨씬 느리지만, 프로세스가 강제 종료되는 것보다는 훨씬 낫습니다.

> 💡 **`/etc/fstab`이 뭔가요?**  
> 서버 부팅 시 자동으로 마운트(연결)할 파일 시스템 목록을 정의한 파일입니다. 여기에 등록하지 않으면 재부팅할 때마다 swap이 해제됩니다.

### 4-3. Swappiness 조정

```bash
echo 'vm.swappiness=10' | sudo tee -a /etc/sysctl.conf
sudo sysctl -p
```

> 💡 **Swappiness가 뭔가요?**  
> RAM이 얼마나 남아있을 때 swap을 쓸 것인지를 결정하는 값입니다 (0~100). 기본값은 60으로, RAM이 꽤 많이 남아있어도 swap을 적극적으로 씁니다. `10`으로 낮추면 RAM이 거의 다 찼을 때만 swap을 사용하도록 바꿔줘서 실제 메모리를 최대한 활용합니다.

---

## 5. Docker 설치

### 5-1. Docker가 뭔가요?

Docker는 애플리케이션을 **컨테이너**라는 독립된 환경에 패키징해서 실행하는 기술입니다.

FastAPI 앱을 실행할 때 필요한 Python 버전, 라이브러리 등을 전부 하나의 박스에 담아서 실행하는 것입니다. 이렇게 하면 서버 환경에 관계없이 동일하게 동작하고, 삭제할 때 컨테이너만 지우면 깔끔하게 제거할 수 있습니다.

### 5-2. Docker 설치 절차

**① 필수 패키지 설치**

```bash
sudo apt install -y ca-certificates curl gnupg
```

> 💡 Docker의 공식 저장소를 신뢰하기 위해 필요한 인증서 관련 패키지들입니다.

**② Docker 공식 GPG 키 등록**

```bash
sudo install -m 0755 -d /etc/apt/keyrings

curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
  sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

sudo chmod a+r /etc/apt/keyrings/docker.gpg
```

> 💡 **GPG 키가 왜 필요한가요?**  
> 인터넷에서 패키지를 받을 때 "이 파일이 진짜 Docker 공식 파일인가?"를 검증합니다. GPG 키로 서명된 패키지만 설치를 허용함으로써 악성 패키지 설치를 방지합니다.

**③ Docker 저장소(Repository) 등록**

```bash
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
```

> 💡 Ubuntu의 기본 apt 저장소에는 오래된 버전의 Docker가 있을 수 있습니다. Docker 공식 저장소를 직접 등록해야 최신 버전을 받을 수 있습니다.

**④ Docker 설치**

```bash
sudo apt update

sudo apt install -y \
  docker-ce \
  docker-ce-cli \
  containerd.io \
  docker-buildx-plugin \
  docker-compose-plugin
```

> 💡 **각 패키지 역할:**
> - `docker-ce`: Docker 엔진 본체 (Community Edition)
> - `docker-ce-cli`: 터미널에서 `docker` 명령어를 사용하기 위한 CLI 도구
> - `containerd.io`: 컨테이너 런타임 (실제로 컨테이너를 실행하는 저수준 엔진)
> - `docker-buildx-plugin`: 멀티 플랫폼 이미지 빌드 플러그인
> - `docker-compose-plugin`: `docker compose` 명령어 지원 플러그인

**⑤ sudo 없이 docker 명령어 사용 설정**

```bash
sudo usermod -aG docker $USER
newgrp docker
```

> 💡 Docker는 기본적으로 root 권한이 필요합니다. 현재 사용자를 `docker` 그룹에 추가해서 `sudo` 없이 사용할 수 있게 합니다. `newgrp docker`는 로그아웃 없이 그룹 변경을 즉시 적용하는 명령어입니다.

**⑥ 설치 확인**

```bash
docker --version
docker compose version
```

아래와 같이 버전 정보가 출력되면 성공입니다.

```
Docker version 27.x.x, build ...
Docker Compose version v2.x.x
```

---

## 6. FastAPI 컨테이너 실행

### 6-1. Docker Compose가 뭔가요?

`docker compose`는 컨테이너 구성을 YAML 파일 하나로 정의하고 관리하는 도구입니다. 환경 변수, 포트, 볼륨 등을 파일로 관리할 수 있어서 매번 긴 `docker run` 명령어를 타이핑하지 않아도 됩니다.

### 6-2. 프로젝트 디렉토리 생성

```bash
mkdir -p ~/youtube-summary/app && cd ~/youtube-summary
```

> 💡 `mkdir -p`는 중간 디렉토리가 없어도 한 번에 생성하는 옵션입니다.

### 6-3. 프로젝트 파일 작성

최소한의 파일로 FastAPI 컨테이너가 정상 동작하는지 먼저 확인합니다.

**app/main.py**

```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/health")
def health_check():
    return {"status": "ok"}
```

**requirements.txt**

```txt
fastapi
uvicorn[standard]
```

**Dockerfile**

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

> 💡 **Dockerfile이 뭔가요?**  
> 컨테이너 이미지를 만드는 설계도입니다. "Python 3.12 이미지를 베이스로 쓰고, 패키지 설치하고, 코드 복사하고, 이 명령어로 실행해라"를 순서대로 정의합니다.

> 💡 **`python:3.12-slim`을 쓰는 이유는?**  
> `slim`은 불필요한 패키지를 제거한 경량 이미지입니다. 일반 `python:3.12` 이미지보다 용량이 훨씬 작아서 e2-micro 같은 제한된 환경에 적합합니다.

**docker-compose.yml**

```yaml
services:
  app:
    build: .
    container_name: youtube-summary
    restart: unless-stopped
    ports:
      - "8000:8000"
    environment:
      - TZ=Asia/Seoul
    env_file:
      - .env
```

> 💡 **각 설정 항목 설명:**
>
> | 항목 | 설명 |
> |---|---|
> | `build: .` | 현재 디렉토리의 Dockerfile로 이미지를 직접 빌드 |
> | `restart: unless-stopped` | 서버 재부팅 시 자동으로 컨테이너 재시작. 수동으로 stop한 경우에는 재시작 안 함 |
> | `ports: "8000:8000"` | 호스트(서버)의 8000 포트 → 컨테이너의 8000 포트로 연결 |
> | `env_file: .env` | `.env` 파일에 정의된 환경 변수를 컨테이너에 주입 |

**.env**

```env
# API 키는 여기에 관리합니다
YOUTUBE_API_KEY=
SUPADATA_API_KEY=
GEMINI_API_KEY=
GMAIL_USER=
GMAIL_APP_PASSWORD=
RECIPIENT_EMAIL=
CHANNEL_IDS=
```

> ⚠️ `.env` 파일은 절대 Git에 커밋하지 마세요. `.gitignore`에 반드시 추가해야 합니다.

### 6-4. 최종 디렉토리 구조 확인

```
~/youtube-summary/
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── .env
└── app/
    └── main.py
```

### 6-5. 컨테이너 빌드 및 실행

```bash
cd ~/youtube-summary
docker compose up -d --build
```

> 💡 **`--build` 옵션이 뭔가요?**  
> 컨테이너를 시작하기 전에 이미지를 새로 빌드합니다. 코드나 `requirements.txt`를 변경했을 때 반드시 붙여줘야 변경 사항이 반영됩니다. 처음 실행할 때도 이미지가 없으므로 `--build`가 필요합니다.

### 6-6. 실행 상태 확인

```bash
# 컨테이너 실행 상태 확인
docker compose ps
```

`STATUS`가 `Up`이면 정상입니다.

```bash
# 실시간 로그 확인
docker compose logs -f app
```

아래와 같은 메시지가 보이면 정상 실행된 것입니다.

```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

로그 보기 종료: `Ctrl + C`

### 6-7. 동작 확인

브라우저 또는 curl로 헬스 체크 엔드포인트를 호출합니다.

```bash
curl http://<GCP_외부_IP>:8000/health
```

아래와 같은 응답이 오면 성공입니다. 🎉

```json
{"status": "ok"}
```

---

## 자주 쓰는 관리 명령어 모음

```bash
# 컨테이너 중지
docker compose stop app

# 컨테이너 재시작
docker compose restart app

# 코드 변경 후 재빌드 & 재시작
docker compose up -d --build

# 실시간 로그 보기
docker compose logs -f app

# 서버 메모리 상태 확인
free -h

# 디스크 사용량 확인
df -h
```

---

## 트러블슈팅

### 접속이 안 될 때

1. GCP 방화벽에서 8000 포트가 열려 있는지 확인
2. `docker compose ps`로 컨테이너가 `Up` 상태인지 확인
3. `docker compose logs app`으로 에러 메시지 확인

### 빌드 중 메모리 부족으로 실패할 때

```bash
free -h  # Swap 사용 여부 확인
```

Swap이 설정되어 있는지 확인하고, 설정되어 있지 않다면 4-2 단계를 다시 진행합니다.

### SSH 접속이 거부될 때

```bash
# 키 파일 권한 확인 및 수정 (600이어야 함)
chmod 600 ~/.ssh/gcp_fastapi
```

SSH 키 파일의 권한이 너무 열려 있으면 SSH 클라이언트가 보안 이유로 키 사용을 거부합니다.

### 코드 변경 후 반영이 안 될 때

`docker compose up -d`만 실행하면 이미지를 새로 빌드하지 않습니다. 코드를 변경했다면 반드시 `--build` 옵션을 붙여주세요.

```bash
docker compose up -d --build
```

---

*다음 단계: API 키 발급 및 유튜브 요약 기능 구현*
