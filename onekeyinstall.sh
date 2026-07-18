#!/usr/bin/env bash
# ITML 一键无人值守安装脚本
# 用法: bash onekeyinstall.sh
# 从 http://scm.closefrp.com/itml/onekeyinstall.sh 下载后自动执行
# 支持: Debian/Ubuntu/CentOS/RHEL/Rocky/AlmaLinux/Arch

set -e

# ── 配置 ────────────────────────────────────────────────────────────────────────
REPO_URL="https://github.com/zqamemz/Immortal-TUI-MEFrp-Launcher.git"
INSTALL_DIR="/opt/sml"
VENV_DIR="$INSTALL_DIR/venv"
BIN_SML="/usr/local/bin/sml"
BIN_SML_INSTALL="/usr/local/bin/sml-install"

# ── 颜色输出 ────────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

info()  { printf "${CYAN}[INFO]${NC} %s\n" "$*"; }
ok()    { printf "${GREEN}[OK]${NC}   %s\n" "$*"; }
warn()  { printf "${YELLOW}[WARN]${NC} %s\n" "$*"; }
fail()  { printf "${RED}[FAIL]${NC} %s\n" "$*"; exit 1; }

# ── 检测包管理器 ────────────────────────────────────────────────────────────────
info "检测系统环境..."
if command -v apt-get &>/dev/null; then
    PKG_MGR="apt"
    SUDO="sudo"
elif command -v dnf &>/dev/null; then
    PKG_MGR="dnf"
    SUDO="sudo"
elif command -v yum &>/dev/null; then
    PKG_MGR="yum"
    SUDO="sudo"
elif command -v pacman &>/dev/null; then
    PKG_MGR="pacman"
    SUDO="sudo"
else
    PKG_MGR="unknown"
    SUDO=""
fi
info "系统包管理器: $PKG_MGR"

# ── 安装系统依赖 ────────────────────────────────────────────────────────────────
info "检查并安装系统依赖 (git, python3)..."

install_pkg() {
    case "$PKG_MGR" in
        apt)    $SUDO apt-get update -qq && $SUDO apt-get install -y git python3 python3-venv python3-pip ;;
        dnf)    $SUDO dnf install -y git python3 python3-pip ;;
        yum)    $SUDO yum install -y git python3 python3-pip ;;
        pacman) $SUDO pacman -Sy --noconfirm git python ;;
        *)
            # 尝试直接检测
            if ! command -v git &>/dev/null; then
                fail "无法自动安装 git，请手动安装后重试。"
            fi
            ;;
    esac
}

MISSING_DEPS=""
command -v git &>/dev/null     || MISSING_DEPS="$MISSING_DEPS git"
command -v python3 &>/dev/null || MISSING_DEPS="$MISSING_DEPS python3"

if [ -n "$MISSING_DEPS" ]; then
    info "缺少依赖:$MISSING_DEPS，正在自动安装..."
    install_pkg || warn "自动安装失败，继续尝试..."
fi

# 再次确认
command -v git &>/dev/null     || fail "git 未安装，请手动安装 git 后重试。"
command -v python3 &>/dev/null || fail "python3 未安装，请手动安装 python3 后重试。"

PYTHON="python3"
PYTHON_VERSION=$($PYTHON --version 2>&1)
info "Python: $PYTHON_VERSION"

MAJOR=$($PYTHON -c "import sys; print(sys.version_info.major)")
MINOR=$($PYTHON -c "import sys; print(sys.version_info.minor)")
if [ "$MAJOR" -lt 3 ] || { [ "$MAJOR" -eq 3 ] && [ "$MINOR" -lt 8 ]; }; then
    fail "Python 版本需要 >= 3.8，当前是 $MAJOR.$MINOR"
fi

# ── 克隆/更新项目 ──────────────────────────────────────────────────────────────
info "准备安装目录: $INSTALL_DIR"
if [ -d "$INSTALL_DIR/.git" ]; then
    info "项目已存在，执行 git pull 更新..."
    cd "$INSTALL_DIR"
    git pull --ff-only || warn "git pull 失败，继续安装..."
else
    info "克隆项目..."
    $SUDO mkdir -p "$(dirname "$INSTALL_DIR")"
    $SUDO git clone "$REPO_URL" "$INSTALL_DIR" \
        || fail "克隆失败，请检查网络连接。"
    cd "$INSTALL_DIR"
fi

# 确保当前用户对安装目录有写权限（如果不是 root 运行）
if [ ! -w "$INSTALL_DIR" ] && [ "$(id -u)" -ne 0 ]; then
    info "当前用户无写权限，修改目录权限..."
    $SUDO chown -R "$(id -u):$(id -g)" "$INSTALL_DIR"
fi

# ── 创建虚拟环境 ────────────────────────────────────────────────────────────────
if [ -d "$VENV_DIR" ]; then
    info "虚拟环境已存在: $VENV_DIR"
else
    info "创建虚拟环境: $VENV_DIR"
    $PYTHON -m venv "$VENV_DIR" || fail "创建虚拟环境失败"
fi

# ── 安装 Python 依赖 ────────────────────────────────────────────────────────────
info "安装 Python 依赖..."
source "$VENV_DIR/bin/activate"
pip install -U pip -q 2>/dev/null || true
pip install -r requirements.txt -q
pip install -e . -q
ok "依赖安装完成"

# ── 生成 /usr/local/bin/sml 包装脚本 ──────────────────────────────────────────
info "生成 sml 命令..."

$PYTHON - "$VENV_DIR" "$BIN_SML" << 'PYEOF'
import sys, os, stat

venv_dir   = sys.argv[1]
bin_sml    = sys.argv[2]
venv_python = os.path.join(venv_dir, "bin", "python")

content = (
    "#!/usr/bin/env bash\n"
    f"# ITML 启动脚本 - 由 onekeyinstall.sh 自动生成\n"
    f"exec \"{venv_python}\" -m sml \"$@\"\n"
)

with open(bin_sml, "w") as f:
    f.write(content)
os.chmod(bin_sml, os.stat(bin_sml).st_mode | stat.S_IEXEC)
print(f"已生成: {bin_sml}")
PYEOF

ok "已安装: $BIN_SML"

# ── 安装 mefrpc ─────────────────────────────────────────────────────────────────
info "安装内置 mefrpc..."
"$VENV_DIR/bin/python" -c "from sml.installer import install; print(install())" 2>/dev/null || ok "mefrpc 安装跳过（首次启动时会自动安装）"

# ── 完成 ────────────────────────────────────────────────────────────────────────
echo ""
printf "${GREEN}╔══════════════════════════════════════════════════════════════════╗${NC}\n"
printf "${GREEN}║  ITML 安装完成！                                          ║${NC}\n"
printf "${GREEN}╠══════════════════════════════════════════════════════════════════╣${NC}\n"
printf "${GREEN}║  启动:  ${NC}sml                                           ║\n"
printf "${GREEN}║  安装目录:  ${NC}$INSTALL_DIR                 ║\n"
printf "${GREEN}║  更新:  ${NC}cd $INSTALL_DIR && git pull && bash onekeyinstall.sh║\n"
printf "${GREEN}║  卸载:  ${NC}rm -rf $INSTALL_DIR $BIN_SML       ║\n"
printf "${GREEN}╚══════════════════════════════════════════════════════════════════╝${NC}\n"
echo ""

# ── 启动引导 ────────────────────────────────────────────────────────────────────
printf "${CYAN}是否现在启动 ITML？[Y/n] ${NC}"
read -r START_NOW
if [[ "$START_NOW" =~ ^[Nn]$ ]]; then
    info "跳过启动。下次运行 sml 即可启动。"
    exit 0
fi

info "启动 ITML..."
exec "$BIN_SML"
