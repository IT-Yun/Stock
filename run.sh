#!/usr/bin/env bash
# ===========================================
# 주식 분석 플랫폼 통합 실행 스크립트
# 백엔드(Python)와 프론트엔드(React)를 동시에 실행합니다.
# 사용법: ./run.sh
# 종료: Ctrl+C
# ===========================================

set -e

# --- 색상 정의 ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# --- 유틸리티 함수 ---
info()    { echo -e "${BLUE}[INFO]${NC} $1"; }
success() { echo -e "${GREEN}[✓]${NC} $1"; }
warn()    { echo -e "${YELLOW}[⚠]${NC} $1"; }
error()   { echo -e "${RED}[✗]${NC} $1"; }

# --- 프로젝트 루트 디렉토리로 이동 ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# --- 백그라운드 프로세스 PID 저장 ---
BACKEND_PID=""
FRONTEND_PID=""

# --- Ctrl+C 시 모든 프로세스 종료 ---
cleanup() {
    echo ""
    info "서버를 종료합니다..."
    if [ -n "$BACKEND_PID" ] && kill -0 "$BACKEND_PID" 2>/dev/null; then
        kill "$BACKEND_PID" 2>/dev/null
        success "백엔드 서버 종료 완료"
    fi
    if [ -n "$FRONTEND_PID" ] && kill -0 "$FRONTEND_PID" 2>/dev/null; then
        kill "$FRONTEND_PID" 2>/dev/null
        success "프론트엔드 서버 종료 완료"
    fi
    exit 0
}
trap cleanup SIGINT SIGTERM

echo ""
echo -e "${BLUE}=================================================${NC}"
echo -e "${BLUE}   주식 분석 플랫폼 통합 실행 스크립트${NC}"
echo -e "${BLUE}=================================================${NC}"
echo ""

# --- 1단계: Python 버전 확인 ---
info "Python 버전을 확인합니다..."
if ! command -v python3 &>/dev/null; then
    error "Python3가 설치되어 있지 않습니다. Python 3.9 이상을 설치해주세요."
    exit 1
fi

PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PYTHON_MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
PYTHON_MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || { [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 9 ]; }; then
    error "Python 3.9 이상이 필요합니다. (현재: $PYTHON_VERSION)"
    exit 1
fi
success "Python $PYTHON_VERSION 확인 완료"

# --- 2단계: Node.js 버전 확인 ---
info "Node.js 버전을 확인합니다..."
if ! command -v node &>/dev/null; then
    error "Node.js가 설치되어 있지 않습니다. Node.js 18 이상을 설치해주세요."
    exit 1
fi

NODE_VERSION=$(node -v | sed 's/v//' | cut -d. -f1)
if [ "$NODE_VERSION" -lt 18 ]; then
    error "Node.js 18 이상이 필요합니다. (현재: v$(node -v | sed 's/v//'))"
    exit 1
fi
success "Node.js $(node -v) 확인 완료"

# --- 3단계: Python 가상환경 설정 ---
info "Python 가상환경을 설정합니다..."
if [ ! -d "backend/venv" ]; then
    warn "가상환경이 없습니다. 새로 생성합니다..."
    python3 -m venv backend/venv
    success "가상환경 생성 완료 (backend/venv)"
else
    success "기존 가상환경을 사용합니다 (backend/venv)"
fi

# 가상환경 활성화
source backend/venv/bin/activate
success "가상환경 활성화 완료"

# --- 4단계: 백엔드 의존성 설치 ---
info "백엔드 의존성을 설치합니다..."
if [ -f "backend/requirements.txt" ]; then
    pip install -q -r backend/requirements.txt
    success "백엔드 의존성 설치 완료"
else
    warn "backend/requirements.txt 파일이 없습니다. 의존성 설치를 건너뜁니다."
fi

# --- 5단계: 프론트엔드 의존성 설치 ---
info "프론트엔드 의존성을 설치합니다..."
if [ -f "frontend/package.json" ]; then
    (cd frontend && npm install --silent)
    success "프론트엔드 의존성 설치 완료"
else
    warn "frontend/package.json 파일이 없습니다. 의존성 설치를 건너뜁니다."
fi

# --- 6단계: 환경 변수 로드 ---
if [ -f ".env" ]; then
    info ".env 파일을 로드합니다..."
    set -a
    source .env
    set +a
    success ".env 파일 로드 완료"
else
    warn ".env 파일이 없습니다. 기본값을 사용합니다. (.env.example을 참고하여 .env 파일을 생성해주세요)"
fi

# --- 7단계: 백엔드 서버 실행 ---
echo ""
info "백엔드 서버를 시작합니다... (포트: ${API_PORT:-8000})"
if [ -f "backend/main.py" ]; then
    (cd backend && python main.py) &
    BACKEND_PID=$!
    sleep 1
    if kill -0 "$BACKEND_PID" 2>/dev/null; then
        success "백엔드 서버 시작 완료 (PID: $BACKEND_PID)"
    else
        error "백엔드 서버 시작에 실패했습니다."
        exit 1
    fi
else
    warn "backend/main.py 파일이 없습니다. 백엔드 서버 시작을 건너뜁니다."
fi

# --- 8단계: 프론트엔드 개발 서버 실행 ---
info "프론트엔드 개발 서버를 시작합니다... (포트: ${FRONTEND_PORT:-5173})"
if [ -f "frontend/package.json" ]; then
    (cd frontend && npm run dev) &
    FRONTEND_PID=$!
    sleep 1
    if kill -0 "$FRONTEND_PID" 2>/dev/null; then
        success "프론트엔드 서버 시작 완료 (PID: $FRONTEND_PID)"
    else
        error "프론트엔드 서버 시작에 실패했습니다."
        exit 1
    fi
else
    warn "frontend/package.json 파일이 없습니다. 프론트엔드 서버 시작을 건너뜁니다."
fi

echo ""
echo -e "${GREEN}=================================================${NC}"
echo -e "${GREEN}   모든 서버가 실행 중입니다!${NC}"
echo -e "${GREEN}   백엔드:    http://localhost:${API_PORT:-8000}${NC}"
echo -e "${GREEN}   프론트엔드: http://localhost:${FRONTEND_PORT:-5173}${NC}"
echo -e "${GREEN}   종료하려면 Ctrl+C를 누르세요.${NC}"
echo -e "${GREEN}=================================================${NC}"
echo ""

# --- 서버가 종료될 때까지 대기 ---
wait
